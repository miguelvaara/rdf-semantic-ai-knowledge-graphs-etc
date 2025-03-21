import csv
import re

def generate_sparql_update(csv_file):
    triples = []
    binds = []

    with open(csv_file, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file, skipinitialspace=True)

        for index, row in enumerate(reader):
            # Homme perustuu ruotsinkieliseen prefLabeliin eli jos sellainen löytyy datasta, niin käsite on jo ysossa ja vientiä ei tehdä.
            # Lisäksi, jos sv preflabel -kentässä on uri, niin se indikoi, että käsite on jo olemassa ja silloinkaan ei viedä.
            # Huom!!! Myöhemmin, muiden kielikuntien kohdalla ei välttämättä ole nyt mainittua ruotsi-ehtoa, ja silloin skriptiä pitää vähän tuunata.
            sv_preflabel_column = "sv preflabel (löytyy lähteistä Nationalencyklopedin, SAO, Wikipedia, Lexvo tms. vakiintunut käyttö)  Tyhjä=luotettavaa sv-muotoa ei ole löydetty. Mahdollinen linkki jo olemassa olevaan YSO-käsitteeseen"
            sv_preflabel = row.get(sv_preflabel_column, "").strip()

            if not sv_preflabel or re.match(r"^https?://", sv_preflabel):
                continue  

            preflabel_fi = row.get("Valittu käsite YSO-sanastossa = preflabel", "").strip()
            concept_label_en = row.get("Kielikunnan nimi englanniksi", "").strip()

            # Vaikka Excel-datassa lukee hidden, niin alt_labels_fi sisältää oikeasti altLabeleita ja sellaisena ne viedään dataan. 
            # En halunnut epäyhtenäistää masterdataa, niin jätin tällaiseksi
            alt_labels_fi = [label.strip() for label in row.get("Piilotetut ohjaustermit = hidden labelit YSO-sanastossa", "").split(", ") if label]
            alt_labels_sv = [label.strip() for label in row.get("sv alternative", "").split(", ") if label]
            singular_pref_fi = row.get("Kielikunnan yksikkömuoto = singular pref", "").strip()
            singular_pref_sv = row.get("sv singular pref", "").strip()
            singular_alt_fi = [label.strip() for label in row.get("Kielikunnan piilotetun ohjaustermin yksikkömuoto = singular alternative", "").split(", ") if label]
            singular_alt_sv = [label.strip() for label in row.get("sv singular alternative", "").split(", ") if label]
            notes = [row.get("pelkästään dataan tuleva note = preflabel sensitiivinen", "").strip(), row.get("Kommenttikenttään tuleva teksti (skos-note)", "").strip()]
            notes = [note for note in notes if note]  # Poistetaan tyhjät arvot

            # Uniikki uri kaikille
            concept_var = f"?uusi_{index}"

            # concept_triples = [
            #     f"{concept_var} rdf:type yso-meta:Concept ;",
            #     f'    skos:prefLabel "{preflabel_fi}"@fi ;',
            #     f'    skos:prefLabel "{concept_label_en}"@en ;',
            #     f'    skos:prefLabel "{sv_preflabel}"@sv ;',
            #     f'    dct:created ?now ;',
            #     f'    yso-meta:hasThematicGroup yso:p26557 ;',
            #     f'    yso-meta:singularPrefLabel "{singular_pref_fi}"@fi ;',
            #     f'    yso-meta:singularPrefLabel "{singular_pref_sv}"@sv ;',
            #     f'    rdfs:subClassOf yso-update:uudet, yso-update:uudetEn, yso-update:uudetSv, yso:p3749 ;'
            #     f'    skos:related yso:p19079 ;'
            # ]

            concept_triples = [
                f"{concept_var} rdf:type yso-meta:Concept ;",
                f'    skos:prefLabel "{preflabel_fi}"@fi ;',
                f'    skos:prefLabel "{concept_label_en}"@en ;',
                f'    skos:prefLabel "{sv_preflabel}"@sv ;',
                f'    dct:created ?now ;',
                f'    yso-meta:hasThematicGroup yso:p26557 ;',
                f'    rdfs:subClassOf yso-update:uudet, yso-update:uudetEn, yso-update:uudetSv, yso:p3749 ;',
                f'    skos:related yso:p19079 ;'
            ] + [
                f'    yso-meta:singularPrefLabel "{singular_pref_fi}"@fi ;' for _ in [singular_pref_fi] if singular_pref_fi
            ] + [
                f'    yso-meta:singularPrefLabel "{singular_pref_sv}"@sv ;' for _ in [singular_pref_sv] if singular_pref_sv
]



            

            # f'    rdfs:subClassOf yso-update:uudet, yso-update:uudetSv, yso-update:uudetEn, yso-update:uudetSme ;'

            for alt in alt_labels_fi:
                concept_triples.append(f'    skos:altLabel "{alt}"@fi ;')
            for alt in alt_labels_sv:
                concept_triples.append(f'    skos:altLabel "{alt}"@sv ;')
            for alt in singular_alt_fi:
                concept_triples.append(f'    yso-meta:singularAltLabel "{alt}"@fi ;')
            for alt in singular_alt_sv:
                concept_triples.append(f'    yso-meta:singularAltLabel "{alt}"@sv ;')
            for note in notes:
                concept_triples.append(f'    dct:editorialNote "{note}"@fi ;')

            triples.append("\n    ".join(concept_triples) + " .")

            # Seuraava on optio, jota tällä kertaa ei päätetty käyttää            
            #triples.append("".join(f'yso:p19079 skos:related {concept_var} .'))

            binds.append(f"BIND( IRI(CONCAT(str(yso:),'g',struuid())) AS {concept_var} )")

    sparql_query = f"""
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX yso: <http://www.yso.fi/onto/yso/>
PREFIX yso-update: <http://www.yso.fi/onto/yso-update/>
PREFIX yso-meta: <http://www.yso.fi/onto/yso-meta/2007-03-02/>

INSERT {{
    """ + "\n\n    ".join(triples) + """
} WHERE {
    BIND( xsd:date(SUBSTR( xsd:string(now()), 0, 11)) AS ?now )
    """ + "\n    ".join(binds) + """
}
""".strip()

    return sparql_query

csv_file_path = "ValmisYSOlle_Etelä-ja-Pohjois-Amerikan_kielikuntatiedot.csv"
sparql_output = generate_sparql_update(csv_file_path)
print(sparql_output)
