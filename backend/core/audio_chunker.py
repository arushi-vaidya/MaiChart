"""
Audio Chunking Utility for Long Audio Files
Think of this as a "smart scissors" that cuts long recordings into digestible pieces
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import math
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AudioChunker:
    """
    Smart audio chunking system - like a train conductor splitting
    long trains into cars that can travel through multiple tunnels
    """

    def __init__(
        self, chunks_folder: Path, chunk_duration: int = 120, overlap: int = 5
    ):
        self.chunks_folder = chunks_folder
        self.chunk_duration = chunk_duration  # seconds
        self.overlap = overlap  # seconds overlap for continuity
        self.chunks_folder.mkdir(exist_ok=True)

        # Check if ffmpeg is available
        self.ffmpeg_available = self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available for audio processing"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("✅ FFmpeg available for audio chunking")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("⚠️ FFmpeg not available - chunking will be limited")
            return False

    def get_audio_duration(self, audio_path: str) -> float:
        """Get audio file duration using ffprobe"""
        if not self.ffmpeg_available:
            return 0.0

        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            try:
                duration = float(result.stdout.strip())
            except ValueError:
                logger.error(f"❌ Invalid audio duration value: {result.stdout.strip()}")
                duration = 0.0
            logger.info(f"📏 Audio duration: {duration:.2f} seconds")
            return duration
        except Exception as e:
            logger.error(f"❌ Error getting audio duration: {e}")
            return 0.0

    def should_chunk_audio(self, audio_path: str, max_duration: int = None) -> bool:
        """Determine if audio file should be chunked"""
        if max_duration is None:
            max_duration = self.chunk_duration

        duration = self.get_audio_duration(audio_path)
        file_size = os.path.getsize(audio_path)

        # OPTIMIZED: Chunk anything longer than 60 seconds or larger than 15MB
        should_chunk = duration > 300 or file_size > (50 * 1024 * 1024)  # 5 minutes OR 50MB


        logger.info(
            f"🤔 Should chunk? {should_chunk} (duration: {duration:.1f}s, size: {file_size / (1024 * 1024):.1f}MB)"
        )
        return should_chunk

    def create_chunks(self, audio_path: str, session_id: str) -> List[Dict]:
        """
        Split audio into overlapping chunks for parallel processing
        Like cutting a long rope into overlapping sections
        """
        if not self.ffmpeg_available:
            logger.error("❌ Cannot chunk audio - FFmpeg not available")
            return [self._create_single_chunk_info(audio_path, session_id)]

        try:
            duration = self.get_audio_duration(audio_path)
            if duration <= self.chunk_duration:
                logger.info("📝 Audio is short enough - no chunking needed")
                return [self._create_single_chunk_info(audio_path, session_id)]

            # Calculate chunk parameters
            total_chunks = math.ceil(duration / (self.chunk_duration - self.overlap))
            chunks_info = []

            logger.info(f"✂️ Creating {total_chunks} chunks from {duration:.1f}s audio")

            for i in range(total_chunks):
                # Calculate chunk timing with overlap
                start_time = i * (self.chunk_duration - self.overlap)
                end_time = min(start_time + self.chunk_duration, duration)

                # Skip if chunk is too short
                if (end_time - start_time) < 5:  # Skip chunks shorter than 5s
                    continue

                chunk_filename = f"{session_id}_chunk_{i:03d}.wav"
                chunk_path = self.chunks_folder / chunk_filename

                # Create chunk using ffmpeg
                success = self._create_audio_chunk(
                    audio_path, str(chunk_path), start_time, end_time - start_time
                )

                if success:
                    chunk_info = {
                        "chunk_id": f"{session_id}_chunk_{i:03d}",
                        "chunk_index": i,
                        "chunk_path": str(chunk_path),
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": end_time - start_time,
                        "file_size": os.path.getsize(chunk_path),
                        "session_id": session_id,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                    chunks_info.append(chunk_info)
                    logger.info(
                        f"📦 Created chunk {i + 1}/{total_chunks}: {start_time:.1f}s-{end_time:.1f}s"
                    )
                else:
                    logger.error(f"❌ Failed to create chunk {i}")

            logger.info(f"✅ Successfully created {len(chunks_info)} chunks")
            return chunks_info

        except Exception as e:
            logger.error(f"❌ Error creating chunks: {e}")
            # Fallback to single chunk
            return [self._create_single_chunk_info(audio_path, session_id)]

    def _create_audio_chunk(
        self, input_path: str, output_path: str, start: float, duration: float
    ) -> bool:
        """Create a single audio chunk using ffmpeg"""
        try:
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i",
                input_path,
                "-ss",
                str(start),
                "-t",
                str(duration),
                "-acodec",
                "pcm_s16le",  # WAV format for better compatibility
                "-ar",
                "16000",  # 16kHz sample rate for transcription
                "-ac",
                "1",  # Mono
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, check=True)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg error creating chunk: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error creating chunk: {e}")
            return False

    def _create_single_chunk_info(self, audio_path: str, session_id: str) -> Dict:
        """Create info for single chunk (no splitting needed)"""
        duration = self.get_audio_duration(audio_path)
        return {
            "chunk_id": f"{session_id}_chunk_000",
            "chunk_index": 0,
            "chunk_path": audio_path,
            "start_time": 0.0,
            "end_time": duration,
            "duration": duration,
            "file_size": os.path.getsize(audio_path),
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "is_original": True,
        }

    def cleanup_chunks(self, session_id: str) -> int:
        """Clean up chunk files for a session"""
        cleaned = 0
        try:
            pattern = f"{session_id}_chunk_*.wav"
            for chunk_file in self.chunks_folder.glob(pattern):
                try:
                    chunk_file.unlink()
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Could not delete {chunk_file}: {e}")

            logger.info(f"🧹 Cleaned up {cleaned} chunk files for session {session_id}")
            return cleaned

        except Exception as e:
            logger.error(f"❌ Error cleaning up chunks: {e}")
            return 0

    def merge_transcripts(self, chunk_results: List[Dict]) -> Dict:
        """
        Merge transcripts from multiple chunks into final result
        Like assembling puzzle pieces back into the complete picture
        """
        try:
            # Sort chunks by index
            sorted_chunks = sorted(chunk_results, key=lambda x: x.get("chunk_index", 0))

            # Combine text with smart overlap handling
            full_text = ""
            total_confidence = 0.0
            total_duration = 0.0
            total_words = 0

            for i, chunk in enumerate(sorted_chunks):
                chunk_text = chunk.get("transcript_text", "").strip()
                chunk_confidence = chunk.get("transcript_confidence", 0.0)
                chunk_duration = chunk.get("duration", 0.0)

                if chunk_text:
                    # Handle overlap by removing duplicate phrases at boundaries
                    if i > 0 and full_text:
                        chunk_text = self._remove_overlap(full_text, chunk_text)

                    full_text += chunk_text
                    if i < len(sorted_chunks) - 1:  # Add space between chunks
                        full_text += " "

                total_confidence += chunk_confidence
                total_duration += chunk_duration
                total_words += len(chunk_text.split()) if chunk_text else 0

            # Calculate average confidence
            avg_confidence = (
                total_confidence / len(sorted_chunks) if sorted_chunks else 0.0
            )

            merged_result = {
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "duration": total_duration,
                "words": total_words,
                "chunks_processed": len(sorted_chunks),
                "status": "completed",
            }

            logger.info(f"🧩 Merged {len(sorted_chunks)} chunks into final transcript")
            logger.info(
                f"📊 Final: {len(full_text)} chars, {total_words} words, {avg_confidence:.3f} confidence"
            )

            return merged_result

        except Exception as e:
            logger.error(f"❌ Error merging transcripts: {e}")
            return {"status": "error", "error": str(e), "text": "", "confidence": 0.0}

    def _remove_overlap(self, previous_text: str, current_text: str) -> str:
        """Remove overlapping words between chunk boundaries"""
        try:
            # Simple overlap removal - look for common phrases at boundaries
            prev_words = previous_text.split()
            curr_words = current_text.split()

            if len(prev_words) < 5 or len(curr_words) < 5:
                return current_text

            # Check for overlap in last 5 words of previous with first 5 words of current
            overlap_size = 0
            for i in range(1, min(6, len(prev_words), len(curr_words)) + 1):
                if prev_words[-i:] == curr_words[:i]:
                    overlap_size = i

            if overlap_size > 0:
                # Remove overlapping words from current chunk
                result = " ".join(curr_words[overlap_size:])
                logger.debug(f"🔗 Removed {overlap_size} overlapping words")
                return result

            return current_text

        except Exception as e:
            logger.warning(f"⚠️ Error removing overlap: {e}")
            return current_text
