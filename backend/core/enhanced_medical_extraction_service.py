"""
Enhanced Medical Extraction Service
OpenAI GPT-4 + BioBERT for Comprehensive Medical Information Extraction
"""

import json
import asyncio
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
import re

# OpenAI imports
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

logger = logging.getLogger(__name__)

class EnhancedMedicalExtractionService:
    """
    Complete Medical Extraction Service
    OpenAI GPT-4 + BioBERT for structured medical information extraction
    """
    
    def __init__(self):
        self.openai_client = None
        self.biobert_ner = None
        self.biobert_tokenizer = None
        self.biobert_model = None
        self.is_loaded = False
        
        # Get API keys from environment
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.enable_extraction = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
        self.biobert_model_name = os.getenv("BIOBERT_MODEL", "dmis-lab/biobert-base-cased-v1.2")
        self.confidence_threshold = float(os.getenv("MEDICAL_EXTRACTION_CONFIDENCE_THRESHOLD", "0.7"))
        
        if not self.openai_api_key:
            logger.warning("⚠️ OPENAI_API_KEY not found. Medical extraction will be disabled.")
            self.enable_extraction = False
    
    async def initialize_models(self):
        """Load OpenAI client and BioBERT models"""
        try:
            if not self.enable_extraction:
                logger.info("🚫 Medical extraction disabled")
                return
                
            logger.info("🚀 Initializing medical extraction models...")
            
            # Initialize OpenAI client
            if self.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
                logger.info("✅ OpenAI client initialized")
            
            # Load BioBERT for Named Entity Recognition
            logger.info("🧬 Loading BioBERT for medical NER...")
            self.biobert_tokenizer = AutoTokenizer.from_pretrained(self.biobert_model_name)
            self.biobert_model = AutoModelForTokenClassification.from_pretrained(self.biobert_model_name)
            
            # Create NER pipeline
            self.biobert_ner = pipeline(
                "ner",
                model=self.biobert_model,
                tokenizer=self.biobert_tokenizer,
                aggregation_strategy="simple",
                device=-1  # CPU only for stability
            )
            
            logger.info("✅ BioBERT loaded successfully")
            self.is_loaded = True
            
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            self.enable_extraction = False
            raise
    
    def create_structured_extraction_prompt(self, transcript: str) -> str:
        """Create optimized prompt for structured medical information extraction"""
        return f"""You are a medical AI assistant specializing in extracting structured information from clinical notes. Extract the following medical information from the given medical note in a structured JSON format:

1. Patient Details (name, age, gender, marital status, residence)
2. Chief Complaints (primary symptoms and duration)
3. Chief Complaint Details (location in body, severity on scale 1-10)
4. Past History (previous illnesses, surgeries)
5. Chronic Diseases (diabetes, hypertension, etc.)
6. Lifestyle (smoking, alcohol, recreational drugs with frequency)
7. Drug History (current medications)
8. Family History (conditions in family members)
9. Allergies (especially medication allergies)
10. Symptoms (all mentioned symptoms)
11. Possible Diseases (based on mentioned symptoms)

Instructions:
- Extract only if clearly mentioned
- Be concise but thorough
- IMPORTANT: Return ALL fields in the JSON structure exactly as shown below, even if no information is found
- For empty fields, use null for string fields and empty arrays [] for list fields
- Prioritize medical relevance
- For allergies, be especially thorough - this is critical patient safety information

Medical Note: "{transcript}"

Output Format JSON:
{{
    "patient_details": {{
        "name": "string or null",
        "age": "string or null", 
        "gender": "string or null",
        "marital_status": "string or null",
        "residence": "string or null"
    }},
    "chief_complaints": ["complaint with duration", ...],
    "chief_complaint_details": [
        {{
            "complaint": "string",
            "location": "string or null",
            "severity": "string or null",
            "duration": "string or null"
        }},
        ...
    ],
    "past_history": ["previous illness/surgery", ...],
    "chronic_diseases": ["disease", ...],
    "lifestyle": [
        {{
            "habit": "string",
            "frequency": "string or null",
            "duration": "string or null"
        }},
        ...
    ],
    "drug_history": ["medication", ...],
    "family_history": ["condition with relation", ...],
    "allergies": ["allergy", ...],
    "symptoms": ["symptom", ...],
    "possible_diseases": ["disease", ...]
}}

Return ONLY the JSON structure, no additional text."""

    async def extract_with_openai(self, transcript: str) -> Dict:
        """Extract structured medical data using OpenAI GPT-4"""
        try:
            if not self.openai_client:
                logger.warning("⚠️ OpenAI client not available")
                return self._create_empty_medical_structure()
                
            prompt = self.create_structured_extraction_prompt(transcript)
            
            logger.info("🤖 Calling OpenAI API for medical extraction...")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a medical AI assistant that extracts structured information from clinical notes. Always return valid JSON in the exact format requested."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=1500,
                top_p=0.9
            )
            
            # Extract JSON from response
            content = response.choices[0].message.content.strip()
            
            # Clean up the response to extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    extracted_data = json.loads(json_str)
                    logger.info("✅ OpenAI extraction successful")
                    return extracted_data
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"Raw content: {content}")
                    return self._create_empty_medical_structure()
            else:
                logger.error("❌ No JSON found in OpenAI response")
                logger.error(f"Raw content: {content}")
                return self._create_empty_medical_structure()
                
        except Exception as e:
            logger.error(f"❌ Error in OpenAI extraction: {e}")
            return self._create_empty_medical_structure()
    
    async def extract_with_biobert(self, transcript: str) -> List[Dict]:
        """Extract medical entities using BioBERT"""
        try:
            if not self.biobert_ner:
                logger.warning("⚠️ BioBERT not available")
                return []
                
            logger.info("🧬 Running BioBERT entity extraction...")
            
            # Process text with BioBERT NER
            entities = self.biobert_ner(transcript)
            
            # Process and categorize entities
            processed_entities = []
            for entity in entities:
                if entity["score"] >= self.confidence_threshold:
                    processed_entities.append({
                        "text": entity["word"],
                        "label": entity["entity_group"],
                        "confidence": entity["score"],
                        "start": entity.get("start", 0),
                        "end": entity.get("end", 0)
                    })
            
            logger.info(f"✅ BioBERT found {len(processed_entities)} high-confidence entities")
            return processed_entities
            
        except Exception as e:
            logger.error(f"❌ Error in BioBERT extraction: {e}")
            return []
    
    def enhance_with_biobert_entities(self, medical_data: Dict, biobert_entities: List[Dict]) -> Dict:
        """Enhance OpenAI results with BioBERT entities"""
        try:
            # Group BioBERT entities by type
            entity_groups = {}
            for entity in biobert_entities:
                label = entity["label"]
                if label not in entity_groups:
                    entity_groups[label] = []
                entity_groups[label].append(entity)
            
            # Enhance symptoms with BioBERT findings
            biobert_symptoms = []
            for entity in entity_groups.get("SIGN_SYMPTOM", []):
                if entity["confidence"] > 0.8:
                    biobert_symptoms.append(entity["text"])
            
            # Merge with existing symptoms, avoid duplicates
            existing_symptoms = set(s.lower() for s in medical_data.get("symptoms", []))
            for symptom in biobert_symptoms:
                if symptom.lower() not in existing_symptoms:
                    medical_data["symptoms"].append(symptom)
            
            # Enhance drug history with BioBERT chemical entities
            biobert_medications = []
            for entity in entity_groups.get("CHEMICAL", []):
                if entity["confidence"] > 0.75:
                    biobert_medications.append(entity["text"])
            
            # Merge medications
            existing_drugs = set(d.lower() for d in medical_data.get("drug_history", []))
            for med in biobert_medications:
                if med.lower() not in existing_drugs:
                    medical_data["drug_history"].append(med)
            
            # Enhance possible diseases with BioBERT disease entities
            biobert_diseases = []
            for entity in entity_groups.get("DISEASE", []):
                if entity["confidence"] > 0.8:
                    biobert_diseases.append(entity["text"])
            
            # Merge diseases
            existing_diseases = set(d.lower() for d in medical_data.get("possible_diseases", []))
            for disease in biobert_diseases:
                if disease.lower() not in existing_diseases:
                    medical_data["possible_diseases"].append(disease)
            
            # Add BioBERT metadata
            medical_data["biobert_enhancement"] = {
                "entities_found": len(biobert_entities),
                "symptoms_added": len([e for e in entity_groups.get("SIGN_SYMPTOM", []) if e["confidence"] > 0.8]),
                "medications_added": len([e for e in entity_groups.get("CHEMICAL", []) if e["confidence"] > 0.75]),
                "diseases_added": len([e for e in entity_groups.get("DISEASE", []) if e["confidence"] > 0.8]),
                "confidence_threshold": self.confidence_threshold
            }
            
            logger.info("✅ Enhanced medical data with BioBERT entities")
            return medical_data
            
        except Exception as e:
            logger.error(f"❌ Error enhancing with BioBERT: {e}")
            return medical_data
    
    async def extract_medical_information(self, transcript: str) -> Dict:
        """
        Main extraction method - OpenAI + BioBERT ensemble
        """
        if not self.is_loaded:
            await self.initialize_models()
        
        if not self.enable_extraction:
            logger.warning("⚠️ Medical extraction disabled")
            return self._create_empty_medical_structure()
        
        try:
            logger.info("🔄 Starting comprehensive medical information extraction...")
            start_time = datetime.utcnow()
            
            # Run OpenAI and BioBERT in parallel
            openai_task = self.extract_with_openai(transcript)
            biobert_task = self.extract_with_biobert(transcript)
            
            medical_data, biobert_entities = await asyncio.gather(openai_task, biobert_task)
            
            # Enhance OpenAI results with BioBERT entities
            enhanced_data = self.enhance_with_biobert_entities(medical_data, biobert_entities)
            
            # Add extraction metadata
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            enhanced_data["extraction_metadata"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": "OpenAI GPT-4 + BioBERT Ensemble",
                "processing_time_seconds": round(processing_time, 2),
                "openai_model": "gpt-4",
                "biobert_model": self.biobert_model_name,
                "biobert_entities_found": len(biobert_entities),
                "confidence_threshold": self.confidence_threshold,
                "extraction_enabled": self.enable_extraction
            }
            
            logger.info(f"✅ Medical extraction completed in {processing_time:.2f}s")
            return enhanced_data
            
        except Exception as e:
            logger.error(f"❌ Error in medical extraction: {e}")
            return self._create_empty_medical_structure()
    
    def _create_empty_medical_structure(self) -> Dict:
        """Create empty medical data structure matching the required format"""
        return {
            "patient_details": {
                "name": None,
                "age": None,
                "gender": None,
                "marital_status": None,
                "residence": None
            },
            "chief_complaints": [],
            "chief_complaint_details": [],
            "past_history": [],
            "chronic_diseases": [],
            "lifestyle": [],
            "drug_history": [],
            "family_history": [],
            "allergies": [],
            "symptoms": [],
            "possible_diseases": [],
            "extraction_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "method": "OpenAI GPT-4 + BioBERT Ensemble",
                "status": "failed or disabled",
                "extraction_enabled": self.enable_extraction
            }
        }

# Global instance
enhanced_medical_extractor = EnhancedMedicalExtractionService()

# Convenience function for easy integration
async def extract_structured_medical_data(transcript: str) -> Dict:
    """
    Easy-to-use function for comprehensive medical information extraction
    """
    return await enhanced_medical_extractor.extract_medical_information(transcript)

if __name__ == "__main__":
    import asyncio
    
    async def test_extraction():
        print("🧪 Testing Enhanced Medical Extraction Service...")
        
        test_transcript = """
        Patient: John Smith, 45-year-old married male from Chicago, presents with severe chest pain for the past 2 hours.
        Pain is located in the center of the chest, radiating to left arm, severity 8/10.
        Past history: Hypertension for 5 years, appendectomy in 2010.
        Current medications: Lisinopril 10mg daily, Metformin 500mg twice daily.
        Family history: Father had myocardial infarction at age 55, mother has diabetes.
        Social history: Smokes 1 pack per day for 20 years, drinks alcohol occasionally.
        Allergies: Penicillin causes rash.
        Physical exam: Blood pressure 160/95, heart rate 110, diaphoretic, anxious.
        Assessment: Possible acute coronary syndrome versus unstable angina.
        """
        
        try:
            result = await extract_structured_medical_data(test_transcript)
            print("✅ Extraction successful!")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Run the test
    asyncio.run(test_extraction())