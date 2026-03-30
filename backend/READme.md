#create .venv on CLI-> python -m venv .venv
#alternative if python not on path, create .venv with powershell: py -m venv .venv

#activate it from C:\Users\pc\Desktop\Alberto\Alberto\Tesi\FRIA_evaluation\FRIA_evaluation\backend>   with:  .venv\Scripts\Activate

#start backend: uvicorn main:app --reload    -> run at localhost:8000

#dependencies to install backend: fastapi, uvicorn, pandas, openpyxl, python-multipart, HTTPException


#check running backend Lib: python -c "import pandas; print(pandas.__file__)"