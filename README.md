# Ísklifuraðstæður

Gróft mat á ísmyndun á íslenskum ísklifursvæðum, reiknað úr veðurathugunum
Veðurstofu Íslands og veðurspá Open-Meteo.

- `index.html` – síðan sjálf. Les `data.json` og reiknar ísstuðulinn í vafranum.
- `scripts/crags.json` – svæðin (nafn, hnit, hæð). Hnit og hæð eru áætluð; lagaðu þau hér.
- `scripts/fetch.py` – sækir mælingar og spá og skrifar `data.json`.
- `.github/workflows/update.yml` – keyrir `fetch.py` tvisvar á dag.

## Uppsetning

1. Settings → Pages → *Deploy from a branch* → `main` / `(root)`.
2. Actions → *Uppfæra veðurgögn* → *Run workflow* til að prófa fyrstu keyrslu.

## Líkanið

Hiti hvers svæðis er veginn úr allt að fjórum næstu sjálfvirku stöðvum (innan 60 km)
og leiðréttur fyrir hæð (0,65° á 100 m). Frostdagur bætir meðalfrosti dagsins við
stuðulinn (mest 8), hlákudagur dregur frá tvöfaldan meðalhita auk 0,3 × úrkomu (mest 20 mm)
í spánni. Stuðullinn er á bilinu 0–60. Líkanið er nánast ókvarðað og tekur ekki tillit til
vatnsframboðs, áttarhorns, sólar eða vinds.

## Gögn

- [Veðurstofa Íslands – veðurathuganir](https://api.vedur.is/weather/)
- [Open-Meteo – veðurspá](https://open-meteo.com/) (ókeypis aðgangur er ekki ætlaður til nota í atvinnuskyni)
- [Ísalp – klifursvæði](https://www.isalp.is/en/category/crag)
