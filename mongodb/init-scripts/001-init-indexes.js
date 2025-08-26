// mongodb/init-scripts/001-init-indexes.js
// MongoDB initialization script to create indexes for better performance

print("🚀 Initializing MaiChart Medical Database...");

// Switch to the medical database
db = db.getSiblingDB('maichart_medical');

print("📋 Creating sessions collection indexes...");
db.sessions.createIndex({ "session_id": 1 }, { unique: true });
db.sessions.createIndex({ "uploaded_at": -1 });
db.sessions.createIndex({ "status": 1 });
db.sessions.createIndex({ "processing_strategy": 1 });
db.sessions.createIndex({ "uploaded_at": -1, "status": 1 });

print("📝 Creating transcripts collection indexes...");
db.transcripts.createIndex({ "session_id": 1 }, { unique: true });
db.transcripts.createIndex({ "created_at": -1 });
db.transcripts.createIndex({ "confidence": -1 });
db.transcripts.createIndex({ "word_count": -1 });
db.transcripts.createIndex({ "transcript_text": "text" });

print("🏥 Creating medical_extractions collection indexes...");
db.medical_extractions.createIndex({ "session_id": 1 }, { unique: true });
db.medical_extractions.createIndex({ "extracted_at": -1 });
db.medical_extractions.createIndex({ "patient_details.name": 1 });
db.medical_extractions.createIndex({ "patient_details.age": 1 });
db.medical_extractions.createIndex({ "allergies": 1 });
db.medical_extractions.createIndex({ "chronic_diseases": 1 });
db.medical_extractions.createIndex({ "possible_diseases": 1 });
db.medical_extractions.createIndex({ "extraction_metadata.method": 1 });

print("🚨 Creating medical_alerts collection indexes...");
db.medical_alerts.createIndex({ "session_id": 1 });
db.medical_alerts.createIndex({ "created_at": -1 });
db.medical_alerts.createIndex({ "priority": 1 });
db.medical_alerts.createIndex({ "alert_type": 1 });
db.medical_alerts.createIndex({ "session_id": 1, "priority": 1 });

print("📊 Creating compound indexes for analytics...");
db.medical_extractions.createIndex({ 
    "extracted_at": -1, 
    "allergies": 1 
});
db.medical_extractions.createIndex({ 
    "patient_details.age": 1, 
    "chronic_diseases": 1 
});

// Create a user for the application (optional, for better security)
try {
    db.createUser({
        user: "maichart_app",
        pwd: "app_password_123",
        roles: [
            { role: "readWrite", db: "maichart_medical" }
        ]
    });
    print("👤 Created application user: maichart_app");
} catch (error) {
    if (error.code === 51003) { // User already exists
        print("👤 Application user already exists: maichart_app");
    } else {
        print("⚠️ Error creating application user: " + error.message);
    }
}

print("✅ Database initialization completed successfully!");
print("📈 Created indexes for sessions, transcripts, medical_extractions, and medical_alerts");