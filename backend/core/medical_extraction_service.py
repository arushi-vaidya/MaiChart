import json
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

# Model imports
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    pipeline,
    BitsAndBytesConfig
)
import torch

logger = logging.getLogger(__name__)

class MedicalExtractionService:
    """
    Complete Medical Extraction Service
    BioMistral-7B + BioBERT Ensemble for FHIR Generation
    """
    
    def __init__(self):
        self.bio_mistral = None
        self.tokenizer = None
        self.biobert_ner = None
        self.is_loaded = False
        
    async def initialize_models(self):
        """Load all models - CPU version (no GPU needed)"""
        try:
            logger.info("🚀 Loading Mistral-7B (CPU version)...")
            
            # Load Mistral-7B - CPU only, no quantization
            self.tokenizer = AutoTokenizer.from_pretrained(
                "mistralai/Mistral-7B-Instruct-v0.2"
            )
            
            self.bio_mistral = AutoModelForCausalLM.from_pretrained(
                "mistralai/Mistral-7B-Instruct-v0.2",
                torch_dtype=torch.float32,  # CPU compatible
                device_map="cpu",           # Force CPU
                low_cpu_mem_usage=True      # Memory optimization
            )
            
            # Set pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            logger.info("✅ Mistral loaded successfully")
            
            # Load BioBERT for NER - CPU version
            logger.info("🧬 Loading BioBERT...")
            self.biobert_ner = pipeline(
                "ner",
                model="dmis-lab/biobert-base-cased-v1.2",
                tokenizer="dmis-lab/biobert-base-cased-v1.2",
                aggregation_strategy="simple",
                device=-1  # CPU only
            )
            
            logger.info("✅ BioBERT loaded successfully")
            self.is_loaded = True
            
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            raise
    
    def create_fhir_prompt(self, transcript: str) -> str:
        """Create optimized prompt for FHIR extraction"""
        return f"""<s>[INST] You are a medical AI assistant. Extract structured medical information from the following clinical transcript and format it as FHIR JSON.

Clinical Transcript:
{transcript}

Extract the following information in FHIR format:
1. Patient demographics (name, age, gender, DOB if mentioned)
2. Medical conditions/diagnoses 
3. Symptoms and complaints
4. Current medications
5. Allergies (if mentioned)
6. Vital signs/observations
7. Procedures performed or planned

Return ONLY valid JSON in this format:
{{
  "patient": {{
    "name": "extracted name or null",
    "age": "extracted age or null", 
    "gender": "extracted gender or null"
  }},
  "conditions": [
    {{
      "condition": "condition name",
      "status": "active/resolved/suspected",
      "severity": "mild/moderate/severe"
    }}
  ],
  "medications": [
    {{
      "medication": "medication name",
      "dosage": "dosage if mentioned",
      "frequency": "frequency if mentioned"
    }}
  ],
  "symptoms": [
    {{
      "symptom": "symptom description",
      "severity": "mild/moderate/severe",
      "duration": "duration if mentioned"
    }}
  ],
  "observations": [
    {{
      "type": "vital sign type",
      "value": "measured value",
      "unit": "unit of measurement"
    }}
  ],
  "allergies": [
    {{
      "allergen": "allergen name",
      "reaction": "reaction description"
    }}
  ]
}}

JSON: [/INST]"""

    async def extract_with_biomistral(self, transcript: str) -> Dict:
        """Extract FHIR data using Mistral - CPU version"""
        try:
            prompt = self.create_fhir_prompt(transcript)
            
            # Tokenize - CPU version
            inputs = self.tokenizer(
                prompt, 
                return_tensors="pt", 
                truncation=True, 
                max_length=2048  # Smaller for CPU
            )
            
            # Generate - CPU version
            with torch.no_grad():
                outputs = self.bio_mistral.generate(
                    **inputs,
                    max_new_tokens=512,  # Smaller for CPU
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Rest stays the same...
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            json_match = re.search(r'JSON:\s*(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return self._create_empty_fhir()
            else:
                return self._create_empty_fhir()
                    
        except Exception as e:
            logger.error(f"Error in Mistral extraction: {e}")
            return self._create_empty_fhir()
    
    async def extract_with_biobert(self, transcript: str) -> List[Dict]:
        """Extract entities using BioBERT"""
        try:
            # Get NER entities
            entities = self.biobert_ner(transcript)
            
            # Process and categorize entities
            processed_entities = []
            for entity in entities:
                processed_entities.append({
                    "text": entity["word"],
                    "label": entity["entity_group"],
                    "confidence": entity["score"],
                    "start": entity.get("start", 0),
                    "end": entity.get("end", 0)
                })
            
            return processed_entities
            
        except Exception as e:
            logger.error(f"Error in BioBERT extraction: {e}")
            return []
    
    def merge_biobert_entities(self, fhir_data: Dict, biobert_entities: List[Dict]) -> Dict:
        """Enhance FHIR data with BioBERT entities"""
        try:
            # Group BioBERT entities by type
            entity_groups = {}
            for entity in biobert_entities:
                label = entity["label"]
                if label not in entity_groups:
                    entity_groups[label] = []
                entity_groups[label].append(entity)
            
            # Enhance conditions with high-confidence entities
            if "conditions" not in fhir_data:
                fhir_data["conditions"] = []
                
            # Add missing conditions from BioBERT
            for entity in entity_groups.get("DISEASE", []):
                if entity["confidence"] > 0.8:  # High confidence only
                    # Check if already exists
                    existing = any(
                        entity["text"].lower() in condition.get("condition", "").lower()
                        for condition in fhir_data["conditions"]
                    )
                    if not existing:
                        fhir_data["conditions"].append({
                            "condition": entity["text"],
                            "status": "suspected",
                            "severity": "unknown",
                            "confidence": entity["confidence"]
                        })
            
            # Add medication entities
            if "medications" not in fhir_data:
                fhir_data["medications"] = []
                
            for entity in entity_groups.get("CHEMICAL", []):
                if entity["confidence"] > 0.7:
                    existing = any(
                        entity["text"].lower() in med.get("medication", "").lower()
                        for med in fhir_data["medications"]
                    )
                    if not existing:
                        fhir_data["medications"].append({
                            "medication": entity["text"],
                            "dosage": "not specified",
                            "frequency": "not specified",
                            "confidence": entity["confidence"]
                        })
            
            return fhir_data
            
        except Exception as e:
            logger.error(f"Error merging BioBERT entities: {e}")
            return fhir_data
    
    async def extract_medical_data(self, transcript: str) -> Dict:
        """
        Main extraction method - runs ensemble
        """
        if not self.is_loaded:
            await self.initialize_models()
        
        try:
            logger.info("🔄 Starting medical data extraction...")
            
            # Run both models in parallel
            fhir_task = self.extract_with_biomistral(transcript)
            biobert_task = self.extract_with_biobert(transcript)
            
            fhir_data, biobert_entities = await asyncio.gather(fhir_task, biobert_task)
            
            # Merge results
            enhanced_fhir = self.merge_biobert_entities(fhir_data, biobert_entities)
            
            # Add metadata
            enhanced_fhir["extraction_metadata"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": "BioMistral + BioBERT Ensemble",
                "biobert_entities_found": len(biobert_entities),
                "processing_time": "calculated_later"
            }
            
            logger.info("✅ Medical extraction completed successfully")
            return enhanced_fhir
            
        except Exception as e:
            logger.error(f"❌ Error in medical extraction: {e}")
            return self._create_empty_fhir()
    
    def _create_empty_fhir(self) -> Dict:
        """Create empty FHIR structure"""
        return {
            "patient": {"name": None, "age": None, "gender": None},
            "conditions": [],
            "medications": [],
            "symptoms": [],
            "observations": [],
            "allergies": [],
            "extraction_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "method": "BioMistral + BioBERT Ensemble",
                "status": "failed"
            }
        }

# Global instance
medical_extractor = MedicalExtractionService()

# Convenience function for easy integration
async def extract_medical_fhir(transcript: str) -> Dict:
    """
    Easy-to-use function for medical FHIR extraction
    """
    return await medical_extractor.extract_medical_data(transcript)

# Add this at the very end of the file
if __name__ == "__main__":
    import asyncio
    
    async def test_extraction():
        print("🧪 Testing Medical Extraction Service...")
        
        test_transcript = """
        Patient John Smith, 45-year-old male, presents with chest pain and shortness of breath. 
        Blood pressure 140/90, heart rate 95. Currently taking lisinopril 10mg daily. 
        Suspected myocardial infarction. Recommend immediate cardiology consult.
        """
        
        try:
            result = await extract_medical_fhir(test_transcript)
            print("✅ Extraction successful!")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Run the test
    asyncio.run(test_extraction())