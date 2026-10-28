FROM python:3.10-slim

RUN apt update && apt upgrade -y && \
    apt install git -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /cvbot

# നിങ്ങളുടെ ഗിറ്റ്‌ഹബിലുള്ള എല്ലാ ഫയലുകളും നേരിട്ട് കോപ്പി ചെയ്യുന്നു
COPY . .

RUN pip3 install -U pip && pip3 install -U -r requirements.txt

# start.sh ഇല്ലാതെ ബോട്ട് നേരിട്ട് സ്റ്റാർട്ട് ചെയ്യുന്നു
CMD ["python3", "bot.py"]
