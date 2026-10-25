# 1. സപ്പോർട്ട് ഉള്ള പുതിയ ഡെബിയൻ വേർഷനിലേക്ക് (bullseye) മാറി
FROM python:3.8-slim-bullseye

# 2. apt കമാൻഡുകൾ ഒരൊറ്റ വരിയാക്കി മാറ്റുകയും ക്യാഷെ ഫയലുകൾ ഒഴിവാക്കുകയും ചെയ്തു
RUN apt update && apt upgrade -y && \
    apt install git -y && \
    rm -rf /var/lib/apt/lists/*

# 3. വർക്കിംഗ് ഡയറക്ടറി സെറ്റ് ചെയ്തു (cd / ചെയ്യേണ്ട ആവശ്യമില്ല)
WORKDIR /cvilla-jan23

# 4. ഫയലുകൾ പുതിയ ഫോൾഡറിലേക്ക് കോപ്പി ചെയ്യുന്നു
COPY requirements.txt ./requirements.txt
COPY start.sh /start.sh

# 5. pip അപ്ഗ്രേഡ് ചെയ്ത് പാക്കേജുകൾ ഇൻസ്റ്റാൾ ചെയ്യുന്നു
RUN pip3 install -U pip && pip3 install -U -r requirements.txt

CMD ["/bin/bash", "/start.sh"]
