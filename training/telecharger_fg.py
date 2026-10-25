import requests
import csv

url = 'https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines'
colonnes = ['surface_habitable_logement', 'periode_construction', 'type_batiment', 'type_energie_principale_chauffage', 'zone_climatique', 'code_postal_ban', 'etiquette_dpe']

with open('dpe_dataset_fg.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=colonnes)
    writer.writeheader()

    total_ecrit = 0
    cible = 2000
    next_url = None
    params = {
        'size': 1000,
        'qs': '(type_batiment:maison OR type_batiment:appartement) AND code_region_ban:93 AND (etiquette_dpe:F OR etiquette_dpe:G)'
    }

    while total_ecrit < cible:
        if next_url is None:
            response = requests.get(url, params=params)
        else:
            response = requests.get(next_url)

        data = response.json()
        results = data.get('results', [])

        if not results:
            break

        for ligne in results:
            if all(c in ligne for c in colonnes):
                writer.writerow({c: ligne[c] for c in colonnes})
                total_ecrit += 1

        next_url = data.get('next')
        print(f'{total_ecrit} lignes écrites...')

        if next_url is None:
            break

    print(f'Terminé : {total_ecrit} lignes dans dpe_dataset_fg.csv')