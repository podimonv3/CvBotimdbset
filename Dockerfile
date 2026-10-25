# 1. നിലവിൽ സപ്പോർട്ട് ഉള്ള ഏറ്റവും പുതിയ ഇമേജ് (Bookworm) ഉപയോഗിക്കുക
FROM python:3.8-slim-bookworm

# 2. പാക്കേജുകൾ ഇൻസ്റ്റാൾ ചെയ്യുക
RUN apt update && apt upgrade -y && \
    apt install git -y && \
    rm -rf /var/lib/apt/lists/*

# 3. വർക്കിംഗ് ഡയറക്ടറി സെറ്റ് ചെയ്യുക
WORKDIR /cvilla-jan23

# 4. ഫയലുകൾ കോപ്പി ചെയ്യുക
COPY requirements.txt ./requirements.txt
COPY start.sh /start.sh

# 5. pip അപ്ഗ്രേഡ് ചെയ്ത് പാക്കേജുകൾ ഇൻസ്റ്റാൾ ചെയ്യുക
RUN pip3 install -U pip && pip3 install -U -r requirements.txt

CMD ["/bin/bash", "/start.sh"]
