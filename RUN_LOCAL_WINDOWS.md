# Run HRG Smart Inventory Pro On Windows

If pip is stuck at `Preparing metadata (pyproject.toml)`, stop it with:

```powershell
Ctrl + C
```

The main app does not need the heavy ML packages to open. Install only the lightweight Flask dependencies:

```powershell
cd "C:\Users\khush\Documents\Codex\2026-05-31\files-mentioned-by-the-user-hrg\outputs\HRG_Smart_Inventory_Pro_Flask"
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
flask --app app seed-demo
flask --app app run
```

Open:

```text
http://127.0.0.1:5000
```

Login:

```text
admin@hrg.com
admin123
```

Optional ML packages are listed separately in:

```text
requirements-ml-optional.txt
```

Install them only if you are using Python 3.12 or Anaconda. Do not install them with Python 3.14.
