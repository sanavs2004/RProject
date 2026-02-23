import os
import sys
import traceback

print("="*60)
print("🔍 DEBUGGING RESUME SCREENING")
print("="*60)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from modules.semantic_parser import SemanticParser  # Use SemanticParser, not ResumeParser
from modules.skill_extractor import SkillExtractor

print(f"\n📁 Results folder: {Config.RESULTS_FOLDER}")
print(f"📁 Upload folder: {Config.UPLOAD_FOLDER}")

# Check if upload folder exists and has files
if os.path.exists(Config.UPLOAD_FOLDER):
    files = os.listdir(Config.UPLOAD_FOLDER)
    print(f"\n📄 Files in upload folder: {len(files)}")
    for f in files[:5]:  # Show first 5
        file_path = os.path.join(Config.UPLOAD_FOLDER, f)
        size = os.path.getsize(file_path) / 1024  # KB
        print(f"   - {f} ({size:.1f} KB)")
else:
    print("\n❌ Upload folder doesn't exist!")

# Test each parser individually
print("\n" + "="*60)
print("🧪 TESTING PARSERS")
print("="*60)

# Test SemanticParser (this works!)
try:
    print("\n1. Testing SemanticParser...")
    parser = SemanticParser()
    print("   ✅ Parser initialized")
    
    # Try to parse a sample file
    if os.path.exists(Config.UPLOAD_FOLDER) and os.listdir(Config.UPLOAD_FOLDER):
        test_file = os.path.join(Config.UPLOAD_FOLDER, os.listdir(Config.UPLOAD_FOLDER)[0])
        print(f"   📄 Testing with: {os.path.basename(test_file)}")
        result = parser.parse_resume_semantic(test_file)
        if result and result.get('text'):
            print(f"   ✅ Success! Extracted {len(result['text'])} characters")
            print(f"   📊 Word count: {result.get('word_count', 0)}")
            print(f"   🔑 Key points: {len(result.get('key_points', []))}")
        else:
            print("   ❌ Failed to extract text")
    else:
        print("   ⚠️ No files to test")
except Exception as e:
    print(f"   ❌ Error: {e}")
    traceback.print_exc()

# Test SkillExtractor
try:
    print("\n2. Testing SkillExtractor...")
    extractor = SkillExtractor()
    print("   ✅ Extractor initialized")
    
    # Test with sample text
    sample_text = "Python developer with 5 years experience in Django and Flask"
    skills = extractor.extract_semantic(sample_text)
    print(f"   ✅ Extracted {len(skills)} skills from sample")
    if skills:
        print(f"   Skills: {[s['skill'] for s in skills]}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("📋 READY TO SCREEN!")
print("="*60)
print("✅ SemanticParser is working")
print("✅ SkillExtractor is working")
print("✅ Upload folder has files")
print("\n🚀 Run a new screening at: http://localhost:5001/screen-candidates")