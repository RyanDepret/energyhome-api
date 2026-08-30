import pandas as pd

df1 = pd.read_csv('dpe_dataset.csv')
df2 = pd.read_csv('dpe_dataset_fg.csv')
df = pd.concat([df1, df2], ignore_index=True)
df = df.drop_duplicates()

df['code_postal_ban'] = df['code_postal_ban'].astype(str).str.zfill(5)
df['departement'] = df['code_postal_ban'].str[:2]

grouped = df.groupby('departement')['zone_climatique'].value_counts()

zones_par_departement = grouped.groupby(level=0).apply(lambda x: x.index[0][1])
print(zones_par_departement)

dict_zones = zones_par_departement.to_dict()
print(dict_zones)

import joblib
joblib.dump(dict_zones, 'zones_climatiques.pkl')
print("Table sauvegardée : zones_climatiques.pkl")