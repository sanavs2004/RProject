import sys
import os

print(f"Current directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")

# Try to import docx2txt
try:
    import docx2txt
    print(f"✅ SUCCESS! docx2txt imported from: {docx2txt.__file__}")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    
    # Check if the package exists in site-packages
    site_packages = [p for p in sys.path if 'site-packages' in p]
    print(f"\nSite packages locations: {site_packages}")
    
    # List contents of site-packages
    for sp in site_packages:
        if os.path.exists(sp):
            print(f"\nContents of {sp}:")
            try:
                files = os.listdir(sp)
                docx_files = [f for f in files if 'docx' in f.lower()]
                print(f"docx related files: {docx_files}")
            except:
                pass