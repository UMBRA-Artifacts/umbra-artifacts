from dark_cookies.Cookie_Dialog_Analyser import CDA
from dark_cookies.CDA_Options import Options_Auto_All

# --- Updated domains to analyse ---
domains = [
"isolarcloud.eu",
"uni-bamberg.de",
"obdev.at",
"lcl.fr",
"wpimg.pl",
"chiesacattolica.it",
"rtpslots.de",
"lvr.de",
"bamf.de",
"eweka.nl",
"myapple.pl",
"contrataciondelestado.es",
"lumni.fr",
"sissa.it",
"nluug.nl",
"aon.at",
"tripadvisor.be",
"man.eu",
"unicredit.it",
"svenskakyrkan.se"
    ]

for domain in domains:
    print(f"\n[RUNNING] {domain}")
    CDA(domain, options=Options_Auto_All())
