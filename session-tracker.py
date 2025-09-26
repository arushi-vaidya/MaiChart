#!/usr/bin/env python3
"""
Session Status Tracker
Track what happened to your streaming session step by step
"""

import os
import sys
import redis
import json
from datetime import datetime
from pathlib import Path

def connect_redis():
    """Connect to Redis"""
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD'),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        redis_client.ping()
        return redis_client
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None

def check_session_status(redis_client, session_id):
    """Check detailed status of a specific session"""
    print(f"🔍 TRACKING SESSION: {session_id}")
    print("=" * 60)
    
    # Check session status in Redis
    session_key = f"session_status:{session_id}"
    session_data = redis_client.hgetall(session_key)
    
    if not session_data:
        print("❌ Session not found in Redis")
        print("   This could mean:")
        print("   • Session expired (data cleaned up)")
        print("   • Session ID is incorrect")
        print("   • Backend didn't process the upload")
        return False
    
    print("✅ Session found in Redis")
    print("\n📋 SESSION DETAILS:")
    print("-" * 30)
    
    # Parse and display session data
    parsed_data = {}
    for key, value in session_data.items():
        try:
            parsed_data[key] = json.loads(value)
        except:
            parsed_data[key] = value
    
    # Key status fields
    status = parsed_data.get('status', 'unknown')
    recording_mode = parsed_data.get('recording_mode', 'unknown')
    step = parsed_data.get('step', 'unknown')
    
    print(f"Status: {status}")
    print(f"Recording Mode: {recording_mode}")
    print(f"Current Step: {step}")
    
    if parsed_data.get('uploaded_at'):
        print(f"Uploaded At: {parsed_data['uploaded_at']}")
    
    # Streaming-specific info
    if recording_mode == 'streaming':
        chunks_received = parsed_data.get('chunks_received', 0)
        total_size = parsed_data.get('total_size', 0)
        last_chunk_received = parsed_data.get('last_chunk_received', False)
        
        print(f"\n📦 STREAMING INFO:")
        print(f"Chunks Received: {chunks_received}")
        print(f"Total Size: {total_size} bytes ({total_size/(1024*1024):.2f} MB)")
        print(f"Last Chunk Received: {last_chunk_received}")
        
        # Check for merged file
        merged_file = parsed_data.get('merged_file_path')
        if merged_file:
            print(f"Merged File: {merged_file}")
            # Check if file exists
            if Path(merged_file).exists():
                file_size = Path(merged_file).stat().st_size
                print(f"Merged File Size: {file_size} bytes ({file_size/(1024*1024):.2f} MB)")
                print("✅ Merged file exists on disk")
            else:
                print("❌ Merged file missing from disk")
    
    # Processing info
    if parsed_data.get('processing_started_at'):
        print(f"\n⚙️ PROCESSING INFO:")
        print(f"Processing Started: {parsed_data['processing_started_at']}")
        
        if parsed_data.get('processing_completed_at'):
            print(f"Processing Completed: {parsed_data['processing_completed_at']}")
        
        processing_strategy = parsed_data.get('processing_strategy', 'unknown')
        print(f"Processing Strategy: {processing_strategy}")
    
    # Transcription info
    transcript_text = parsed_data.get('transcript_text')
    if transcript_text:
        print(f"\n📝 TRANSCRIPTION INFO:")
        print(f"Transcript Length: {len(transcript_text)} characters")
        print(f"Transcript Confidence: {parsed_data.get('transcript_confidence', 'unknown')}")
        print(f"Word Count: {len(transcript_text.split())} words")
        print(f"Preview: {transcript_text[:200]}...")
    else:
        print(f"\n❌ NO TRANSCRIPT FOUND")
    
    # Medical extraction info  
    medical_queued = parsed_data.get('medical_extraction_queued', False)
    medical_status = parsed_data.get('medical_extraction_status', 'not_started')
    
    print(f"\n🏥 MEDICAL EXTRACTION INFO:")
    print(f"Medical Extraction Queued: {medical_queued}")
    print(f"Medical Extraction Status: {medical_status}")
    
    if parsed_data.get('medical_extraction_queued_at'):
        print(f"Medical Extraction Queued At: {parsed_data['medical_extraction_queued_at']}")
    
    if parsed_data.get('medical_extraction_completed_at'):
        print(f"Medical Extraction Completed At: {parsed_data['medical_extraction_completed_at']}")
    
    # Check if medical data exists
    medical_data_key = f"medical_data:{session_id}"
    medical_data_exists = redis_client.exists(medical_data_key)
    print(f"Medical Data Exists in Redis: {medical_data_exists}")
    
    if medical_data_exists:
        medical_data = redis_client.hgetall(medical_data_key)
        if medical_data.get('medical_data'):
            try:
                parsed_medical = json.loads(medical_data['medical_data'])
                print(f"Medical Data Fields: {list(parsed_medical.keys())}")
                
                # Show key medical info
                patient = parsed_medical.get('patient_details', {})
                if patient.get('name'):
                    print(f"Patient Name: {patient['name']}")
                
                allergies = parsed_medical.get('allergies', [])
                if allergies:
                    print(f"🚨 Allergies Found: {', '.join(allergies)}")
                
                conditions = parsed_medical.get('possible_diseases', [])
                if conditions:
                    print(f"🔍 Possible Conditions: {', '.join(conditions[:3])}")
                    
            except:
                print(f"Medical Data Size: {len(medical_data['medical_data'])} characters")
    
    # Error info
    if parsed_data.get('error'):
        print(f"\n❌ ERROR FOUND:")
        print(f"Error: {parsed_data['error']}")
        print(f"Error Timestamp: {parsed_data.get('error_timestamp', 'unknown')}")
    
    # Warnings
    if parsed_data.get('warning'):
        print(f"\n⚠️ WARNING:")
        print(f"Warning: {parsed_data['warning']}")
    
    return True

def check_file_system(session_id):
    """Check if files exist on file system"""
    print(f"\n📁 FILE SYSTEM CHECK:")
    print("-" * 30)
    
    # Check backend directories
    backend_dirs = {
        'uploads': Path('backend/uploads'),
        'chunks': Path('backend/chunks'), 
        'transcripts': Path('backend/transcripts')
    }
    
    files_found = []
    
    for dir_name, dir_path in backend_dirs.items():
        if not dir_path.exists():
            print(f"❌ {dir_name.title()} directory not found: {dir_path}")
            continue
            
        # Look for files related to this session
        session_files = list(dir_path.glob(f"*{session_id}*"))
        session_files.extend(list(dir_path.glob(f"*streaming_{session_id}*")))
        
        if session_files:
            print(f"✅ Found {len(session_files)} files in {dir_name}:")
            for file_path in session_files:
                file_size = file_path.stat().st_size
                print(f"   {file_path.name} ({file_size} bytes)")
                files_found.append(str(file_path))
        else:
            print(f"⚠️ No files found in {dir_name} for session {session_id}")
    
    return files_found

def check_streams_for_session(redis_client, session_id):
    """Check if session appears in any Redis streams"""
    print(f"\n📡 REDIS STREAMS CHECK:")
    print("-" * 30)
    
    streams_to_check = [
        "audio_input",
        "audio_chunks", 
        "medical_extraction_queue"
    ]
    
    for stream_name in streams_to_check:
        try:
            # Read recent messages from stream
            messages = redis_client.xread({stream_name: '0'}, count=100)
            
            session_found = False
            for stream, stream_messages in messages:
                for message_id, fields in stream_messages:
                    # Check if this message is for our session
                    msg_session_id = fields.get('session_id', '').strip('"')  # Remove JSON quotes
                    if msg_session_id == session_id:
                        session_found = True
                        print(f"✅ Found session in stream '{stream_name}':")
                        print(f"   Message ID: {message_id}")
                        print(f"   Message Type: {fields.get('type', 'unknown')}")
                        print(f"   Queued At: {fields.get('queued_at', 'unknown')}")
            
            if not session_found:
                print(f"⚠️ Session not found in stream '{stream_name}'")
                
        except redis.ResponseError:
            print(f"❌ Stream '{stream_name}' does not exist")
        except Exception as e:
            print(f"❌ Error checking stream '{stream_name}': {e}")

def suggest_next_steps(session_data, files_found):
    """Suggest what to do next based on current status"""
    print(f"\n💡 NEXT STEPS:")
    print("-" * 30)
    
    if not session_data:
        print("1. Check if backend is running:")
        print("   python backend/app.py")
        print("2. Check backend logs for errors")
        return
    
    status = session_data.get('status', 'unknown')
    recording_mode = session_data.get('recording_mode', 'unknown')
    transcript_text = session_data.get('transcript_text')
    medical_queued = session_data.get('medical_extraction_queued', False)
    
    if recording_mode == 'streaming' and status == 'recording':
        print("❌ Session stuck in 'recording' status")
        print("1. The streaming session wasn't properly finalized")
        print("2. Check if the last chunk was marked as final")
        print("3. Restart the backend server")
    
    elif status == 'processing':
        print("⏳ Session is still processing")
        print("1. Wait for transcription to complete")
        print("2. Check transcription worker logs:")
        print("   tail -f backend/logs/transcription_worker.log")
    
    elif status == 'completed' and transcript_text:
        if medical_queued:
            print("✅ Transcription completed, medical extraction queued")
            print("1. Check medical extraction worker is running:")
            print("   python backend/workers/enhanced_medical_extraction_worker.py")
            print("2. Check medical extraction logs")
        else:
            print("⚠️ Transcription completed but medical extraction not queued")
            print("1. Manually trigger medical extraction:")
            print(f"   curl -X POST http://localhost:5001/api/trigger_medical_extraction/{session_data.get('session_id', '')}")
    
    elif status == 'error':
        error = session_data.get('error', 'Unknown error')
        print(f"❌ Session failed with error: {error}")
        print("1. Check backend logs for detailed error")
        print("2. Try re-uploading the audio")
    
    else:
        print(f"🤔 Unusual status: {status}")
        print("1. Check backend and worker logs")
        print("2. Restart all services")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python session_tracker.py <session_id>")
        print("Example: python session_tracker.py 6d9a311e-45ee-4079-9833-99d41dfe4ef4")
        return
    
    session_id = sys.argv[1].strip()
    
    print("🔍 MAICHART SESSION TRACKER")
    print("=" * 60)
    print(f"Tracking session: {session_id}")
    print()
    
    # Connect to Redis
    redis_client = connect_redis()
    if not redis_client:
        return
    
    # Check session status
    session_exists = check_session_status(redis_client, session_id)
    
    # Check file system
    files_found = check_file_system(session_id)
    
    # Check streams
    check_streams_for_session(redis_client, session_id)
    
    # Get session data for suggestions
    session_data = None
    if session_exists:
        session_key = f"session_status:{session_id}"
        raw_data = redis_client.hgetall(session_key)
        session_data = {}
        for key, value in raw_data.items():
            try:
                session_data[key] = json.loads(value)
            except:
                session_data[key] = value
    
    # Suggest next steps
    suggest_next_steps(session_data, files_found)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Cancelled by user")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()