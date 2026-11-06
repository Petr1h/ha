# Topení - řízení kotle podle vah místností

Jeden **automation blueprint** (`heating_control.yaml`), který se celý nastavuje v GUI. Kotel Viessmann BOHA-25 se spíná jedním relé (zap/vyp). Rozhodnutí vychází z **vážené poptávky**: každá místnost přispívá `váha × deficit`, kde `deficit = max(0, cílová − aktuální teplota)` v K.

Cílová verze: HA 2026.10 (HA OS). Blueprint nevyžaduje YAML packages ani vygenerované soubory.

## Instalace

1. Zkopírujte `blueprints/automation/petr1h/heating_control.yaml` do `config/blueprints/automation/petr1h/` (nebo přes Nastavení → Automatizace → Blueprinty → Importovat, pokud ho publikujete).
2. Volitelné pomocné entity (režim, topná sezóna, textový stav, poptávka pro graf): `helpers/heating_helpers.yaml` do `config/packages/` (nebo stejné helpery vytvořte v GUI). Po přidání restart HA.
3. **Nastavení → Automatizace a scény → Blueprinty → „Topení - řízení kotle podle vah místností“ → Vytvořit automatizaci.**
4. Vyplňte: **Relé kotle** (jediný povinný údaj) a v sekci **Místnosti** u každé místnosti její **hlavice (TRV)**. Místnosti přidáte tlačítkem přidat pod seznamem a odeberete v menu položky (viz níže). Místnost bez hlavice se ignoruje. Vše ostatní je volitelné a lze doplnit později (upravit automatizaci).
5. Zapněte `input_boolean.heating_season` (pokud ho používáte, je po vytvoření vypnutý, kotel je tedy vypnutý).

### Co je v blueprintu (sbalené sekce)

| Sekce | Obsah |
|---|---|
| Kotel | relé, topná sezóna, režim / preset (none, away, comfort, eco, home, sleep, work from home, vacation), rozvrh |
| Dočasná ruční změna | stavový helper, sledované hlavice, doba trvání (výchozí 60 min) |
| Prahy, časy a ochrany | práh zapnutí/vypnutí, min. doba zapnutí/vypnutí, min. počet otevřených ventilů, protimrazový start, chování při selhání |
| Cílové teploty podle presetu | comfort, eco, home, sleep, away, work from home, mráz (výchozí pro všechny místnosti) |
| Poptávka a čidla | necitlivost, strop deficitu, limit zastaralých dat |
| Ovládání hlaviček | tolerance cíle, vynucení režimu `heat`, posílání externí teploty do Z2M |
| ViCare a upozornění | entita hořáku (read-only), prodleva, vlastní akce upozornění (např. `notify`) |
| Výstupy a ladění | textový a číselný helper se stavem, logbook, podrobný log |
| Místnosti | libovolný počet místností (přidat / odebrat): název, TRV (více kusů), externí čidlo, zdroj teploty, **váha**, posun cíle, korekce čidla, okenní kontakt, „topit vždy“, **vlastní teplota pro každý preset** |

### Přidání a odebrání místností

Blueprint nemůže mít vlastní tlačítko „AddRoom“ ani dynamicky vytvářet vstupy. Místnosti jsou proto jeden vstup typu `object` (seznam položek), jehož editor v GUI má tlačítko pro přidání položky a menu pro její odebrání. Počet místností není omezen. Změnu uložíte uložením automatizace.

- Nepovinná pole, která u položky nevyplníte, mají výchozí hodnoty: zdroj = TRV, váha = 5, posun = 0, korekce = 0, topit vždy = vypnuto.
- Seznam je předvyplněný vašimi 12 místnostmi (názvy a váhy jsou návrh) bez hlavic, takže nepoužité položky se ignorují. Nepotřebné smažte.
- Pokud editor položek v GUI nepoužijete, lze seznam upravit v YAML automatizace (`use_blueprint → input → rooms`): `- {name: Obývák, trvs: [climate.obyvak], weight: 8}`.
- **Upgrade ze starší verze (12 pevných slotů)** nelze přenést automaticky: vstupy `r1_*` … `r12_*` už neexistují a automatizaci je nutné znovu nastavit.

## Presety a teploty po místnostech

Preset se vybírá v `input_select` (pole **Režim / preset**, helper `heating_mode`). Rozpoznané volby (bez ohledu na velikost písmen, `_` a `-` se berou jako mezera): `none`, `away`, `comfort`, `eco`, `home`, `sleep` (i `night`), `work from home` (i `work_from_home`, `wfh`) a `vacation`. Jiná hodnota se bere jako `none`.

| Preset | Cíl místnosti |
|---|---|
| none | rozvrh: zapnut = comfort, vypnut (nebo žádný rozvrh = comfort) = eco |
| comfort / eco / home / work from home | příslušná teplota |
| sleep | teplota sleep (u místnosti s „topit vždy“ comfort) |
| away | teplota away |
| vacation | mráz |

Každý preset má **globální teplotu** (sekce Cílové teploty podle presetu) a u každé místnosti lze zadat **vlastní teplotu** (`t_away`, `t_comfort`, `t_eco`, `t_home`, `t_sleep`, `t_work`). Zadaná teplota místnosti se použije přesně tak, jak je (posun cíle se nepřičítá). Nezadaná = globální teplota + posun cíle. Otevřené okno a vacation vždy dávají mráz.

Příklad: `work from home` s `t_work: 21` u pracovny a `t_work: 20` u obýváku nastaví pracovnu na 21 a obývák na 20, ostatní místnosti dostanou globální teplotu pro work from home.

Změna oproti starší verzi: preset `home` má pevnou teplotu a rozvrh už neřídí (rozvrh platí jen pro `none`). `night_temp` se jmenuje v GUI „Teplota presetu sleep“. Helper `heating_mode` má nové volby, existující helper upravte ručně.

## Dočasná ruční změna (otočení hlavice)

Když na hlavici otočíte kolečkem, nová teplota se **na dobu 60 min** (nastavitelné 15 až 240 min) zachová a rozvrh ani preset ji nepřepíšou. Funguje celé v Home Assistantu, vestavěný dočasný režim hlavice se nepoužívá. Pokud je pole **Textový helper pro stav dočasných změn** prázdné, funkce je vypnutá a ruční změna se přepíše jako dříve.

### Zapnutí

1. Vytvořte helpery z `helpers/heating_helpers.yaml`: `input_text.heating_override_store` (max 255) a volitelně `input_number.heating_override_duration`.
2. V sekci **Dočasná ruční změna** vyberte stavový helper, **všechny hlavice**, u kterých se má změna sledovat (seznam se musí zadat znovu, spouštěče automatizace nemohou brát entity ze seznamu místností), a případně helper s dobou trvání.

### Chování

| Situace | Výsledek |
|---|---|
| Otočení kolečka na jinou teplotu než cíl | Dočasná změna této hlavice s novou teplotou, platí celou dobu od otočení |
| Další otočení během změny | Nová teplota a **celá doba znovu od začátku** |
| Změna rozvrhu, presetu nebo posunu během změny | Hlavice drží ruční teplotu |
| Uplynutí doby | Změna zanikne, **vypočítá se aktuální běžný cíl** a zapíše se do hlavice (starý cíl se neobnovuje). Probíhá při nejbližším běhu, tedy do 1 min |
| Kolečko otočeno zpět na běžný cíl během změny | Změna se zruší |
| Otevřené okno nebo preset vacation | Má přednost: cíl je mráz, změna se ignoruje (čas běží dál, po zavření okna pokračuje) |
| Restart HA | Konec platnosti je uložen jako absolutní čas, změna pokračuje a časovač se nespouští znovu. Co už vypršelo, se hned vrátí pod běžné řízení |
| Více hlavic | Každá hlavice má vlastní změnu. Poptávka místnosti počítá s průměrem cílů jejích hlavic |

Tolerance „stejné jako běžný cíl“ je **Tolerance cílové teploty** (výchozí 0,4 °C), nastavte ji pod krok hlavice (0,5 °C), jinak se změna o 0,5 °C nepozná.

### Jak se pozná ruční otočení od zápisu z HA

Hlavice po každé změně cíle (i té, kterou zapsal HA) hlásí nový cíl a automatizace se na to spustí. Rozlišují se dva případy:

1. **Před každým zápisem** si automatizace do stavového helperu poznamená „zapsal jsem do hlavice X teplotu T“. Když hlavice T nahlásí, je to potvrzení vlastního zápisu: záznam se spotřebuje a nic se neděje. Záznamů může být u hlavice víc (zápis 21, krátce poté 20, hlavice se probudí a hlásí postupně 21 a 20), takže opožděné hlášení nevadí. Záznam platí 10 min, pak se zapomene (hlavice mimo dosah).
2. **Teplota, kterou HA nezapsal** a která se liší od běžného cíle (o víc než tolerance), je otočení kolečka. Samotné porovnání s rozvrhem by nestačilo, právě proto se zápisy evidují.

Stavový helper má tvar `počet_hlavic|změny|zápisy`, kde změna je `index,teplota×10,konec platnosti v minutách epochy` a index je pořadí hlavice v seznamu sledovaných hlavic. Změní-li se **počet** sledovaných hlavic, uložený stav se zahodí. Při přeřazení hlavic při aktivní změně může být změna přiřazena jiné hlavici do vypršení, proto seznam za provozu raději jen doplňujte na konec.

### Přidání další hlavice

1. Přidejte hlavici do místnosti v sekci **Místnosti**.
2. Přidejte ji i do seznamu **Hlavice sledované kvůli ruční změně** (nejlépe na konec).
3. Uložte automatizaci. Protože se změnil počet sledovaných hlavic, uložený stav se jednorázově zahodí a případné běžící změny skončí.

### Test scénáře (v HA, stopa automatizace)

1. Běžná změna rozvrhu: cíl se zapíše, hlavice ho potvrdí, v logbooku žádná „ruční změna“.
2. Otočte kolečko: v logbooku „Ruční změna na climate.x“, `input_text` obsahuje záznam.
3. Otočte znovu o 30 min později: konec platnosti se posune o celou dobu.
4. Změňte rozvrh během změny: hlavice drží ruční teplotu.
5. Po vypršení: do hlavice se zapíše aktuální běžný cíl.
6. Restartujte HA během změny: změna pokračuje do původního konce.
7. Zápis z HA a pozdní hlášení hlavice: nic se nevytvoří.

## Jak to rozhoduje

| Téma | Rozhodnutí |
|---|---|
| Vzorec | `poptávka = Σ váha × min(deficit, strop)` přes místnosti s deficitem ≥ necitlivost. Jedna málo důležitá místnost sama kotel nezapne. |
| Práh | Místnost s váhou `w` sama zapne kotel při deficitu `práh / w` (práh 6: váha 8 → 0,75 K, váha 2 → 3 K). Váha 0 = místnost kotel nikdy nespustí. |
| Hystereze | Zapnout při poptávce ≥ 6, vypnout při ≤ 2 (výchozí hodnoty). |
| Ochrana relé | Min. doba zapnutí a vypnutí 10 min a min. 1 otevřený ventil (`hvac_action = heating`). |
| Mráz | Místnost pod protimrazovou teplotou vynutí start (s min. časy a otevřenými ventily). |
| Selhání | Nedostupné relé nebo žádná místnost → relé „vypnout“ (nebo „ponechat“) + upozornění. |
| Zdroj teploty | Vybraný zdroj (TRV / externí), při nedostupnosti nebo zastaralosti automaticky druhý. Místnost bez platné teploty se do poptávky nepočítá a hlásí se. |
| Cíl | Podle presetu (viz níže). Vacation a otevřené okno: mráz. Cíl nikdy neklesne pod mráz. |

Automatizace běží každou minutu, při změně relé a (při zapnuté dočasné změně) při každém hlášení cíle z hlavice; běhy se řadí do fronty (`mode: queued`). Příkazy do TRV se posílají jen při rozdílu cíle, ne periodicky.

## Zdroj teploty a TRV-ZBT (ověřeno v dokumentaci Z2M)

- Z2M vystavuje `external_temperature_input` (0–99,9 °C) a `temperature_sensor_select` (`local_temperature` / `remote_temperature` / `remote_source_offline`). Synchronizaci externí hodnoty musí zajistit HA. Blueprint ji posílá přes `mqtt.publish` (volba „Posílat externí teplotu do TRV“, výchozí vypnuto, interval 5 min, jen u místností s externím čidlem).
- Název zařízení v Z2M (friendly name) se bere z názvu zařízení climate entity. Pokud je v HA přejmenované, MQTT příkazy nebudou fungovat.
- TRV-ZBT nemá `preset`. Režim `auto` by spustil jeho vlastní týdenní program, proto blueprint výchozím nastavením vynutí `heat`.
- Ruční změna teploty na hlavici se při zapnuté funkci Dočasná ruční změna zachová na nastavenou dobu, jinak se přepíše při dalším rozdílu s cílem.
- Chování TRV při výpadku HA/MQTT (`remote_source_offline`) není v dokumentaci popsané, ověřte na jednom kuse.

## Dashboard

`helpers/heating_dashboard.yaml` je jednoduchý dashboard (režim, sezóna, relé, stav a důvod, poptávka). Jednotlivé místnosti blueprint jako entity nevystavuje (blueprint nemůže vytvářet senzory). Podrobnosti po místnostech jsou ve stopě automatizace (Nastavení → Automatizace → Stopy) a po zapnutí „Podrobný log“ v logu HA.

## Test plán

1. Vytvořte automatizaci jen s relé a jednou místností. Spusťte ji ručně a otevřete **Stopy**: v `room_data` uvidíte teplotu, cíl, deficit a poptávku.
2. Snižte cíl místnosti (posun cíle) nebo ji v testu zchlaďte. Místnost s nízkou váhou sama: `decision: off`, důvod „pod prahem zapnutí“. Vysoká váha: kotel se zapne a v logbooku je záznam s důvodem.
3. Hned po sepnutí snižte poptávku: relé zůstane do uplynutí min. doby zapnutí.
4. Odpojte relé: upozornění „Relé kotle není dostupné“ do prodlevy.
5. Vyplňte entitu hořáku ViCare: při zapnutém relé a neběžícím hořáku déle než prodleva přijde upozornění.

## Co není ověřeno a otevřené body

- **Blueprint nebyl načten ve skutečném HA.** To platí i pro editor seznamu místností (`object` selektor s `fields`, `multiple`, `label_field`): chování GUI je třeba ověřit při prvním otevření. Logika šablon byla ověřena offline (testovací skript byl odstraněn), schéma blueprintu proti schématu v HA jen ručně (hlavička, sekce, názvy vstupů). Při prvním vytvoření automatizace sledujte `Nastavení → Systém → Protokoly`.
- **Fail-safe relé při výpadku HA**: zatím nerozhodnuto, závisí na nastavení relé (výchozí stav po ztrátě spojení/napájení, NO/NC).
- Dočasná ruční změna: spouštěč `state` s prázdným seznamem hlavic (výchozí stav, funkce vypnutá) a s `attribute: temperature` jsem v HA neověřil. Pokud HA prázdný seznam odmítne, vyberte aspoň jednu hlavici. Chování probuzení baterie TRV-ZBT (zpoždění hlášení) je ošetřeno 10min záznamem zápisů, skutečné zpoždění ověřte v provozu.
- Neznámé: entity ViCare (hořák), vlastní program kotle, které místnosti mají „topit vždy“, okenní kontakty, externí čidla.
- Váhy se mění úpravou automatizace (ne za běhu z dashboardu). Ruční přepsání teploty s časovačem a detekce okna podle poklesu teploty nejsou implementované. Okenní kontakt podporován.
- Blueprint se generuje ze `tools/heating_control.template.yaml` skriptem `tools/generate_blueprint.py` (skript jen vloží výchozí seznam místností). Při změnách upravujte šablonu a skript spusťte znovu.
