import pandas as pd
import numpy as np
import re

#helpers for normalization
DIACRITICS = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
WEAK_LETTERS_PATTERN = re.compile(r"[اويىأةآأإؤئء]")

def undiatratize(text):
    return DIACRITICS.sub("", str(text)) if text is not None else ""

def remove_weak_letters(text):
    if text is None:
        return ""
    s = undiatratize(text)
    s = s.replace("،", " ")
    s = re.sub(r"[^\w\s\u0600-\u06FF]", "", s)
    s = WEAK_LETTERS_PATTERN.sub("", s)
    return re.sub(r"\s+", " ", s).strip()

def extract_pos(tag):
    if tag is None:
        return None
    parts = str(tag).split("_")
    return parts[-1]

#load MADAR lexicon
df = pd.read_csv("MADAR_Lexicon_v1.0.tsv", sep="\t")
columns = ["English", "French", "MSA", "Dialect", "CODA", "MSA_lemma_POS"]
df = df[columns]
df["POS"] = df["MSA_lemma_POS"].apply(extract_pos)

#compute MSA frequency
msa_freq = pd.read_csv("MSA_freq_lists.tsv", sep="\t", header=None, names=["Word", "Frequency"])
msa_freq["Word"] = msa_freq["Word"].apply(undiatratize).str.strip()
msa_dict = dict(zip(msa_freq["Word"], msa_freq["Frequency"]))

def get_msa_freq(text):
    parts = [undiatratize(p).strip() for p in str(text).split("،") if p.strip()]
    return sum(msa_dict.get(p, 0) for p in parts)

df["MSA_Frequency"] = df["MSA"].apply(get_msa_freq)

#compute dialect frequency
da_freq = pd.read_csv("DA_freq_lists.tsv", sep="\t", header=None, names=["Word", "Frequency"])
da_freq["Word"] = da_freq["Word"].str.strip()
da_freq["Frequency"] = pd.to_numeric(da_freq["Frequency"], errors="coerce")
da_dict = dict(zip(da_freq["Word"], da_freq["Frequency"]))

def get_da_freq(text):
    text = re.sub(r"[^\w\s]", "", str(text))
    return sum(da_dict.get(w, 0) for w in text.split())

df["DA_Frequency"] = df["CODA"].apply(get_da_freq)

#ASim: check similarity after normalization 
def compute_asim(row):
    cod = remove_weak_letters(row["CODA"])
    msa_list = [remove_weak_letters(p) for p in str(row["MSA"]).split("،")]
    return int(cod != "" and cod in msa_list)

df["ASim"] = df.apply(compute_asim, axis=1)

#map dialect cities to regions
DIA_LABEL_TO_REGION = {
    "RAB": "Morocco+Algeria", "FES": "Morocco+Algeria", "ALG": "Morocco+Algeria",
    "TUN": "Tunisia+Libya", "SFA": "Tunisia+Libya", "BEN": "Tunisia+Libya", "TRI": "Tunisia+Libya",
    "ALX": "Egypt+Sudan", "CAI": "Egypt+Sudan", "ASW": "Egypt+Sudan", "KHA": "Egypt+Sudan",
    "ALE": "Syria, Lebanon, Jordan, Palestine", "DAM": "Syria, Lebanon, Jordan, Palestine", "BEI": "Syria, Lebanon, Jordan, Palestine",
    "AMM": "Syria, Lebanon, Jordan, Palestine", "JER": "Syria, Lebanon, Jordan, Palestine", "SAL": "Syria, Lebanon, Jordan, Palestine",
    "BAG": "Iraq", "BAS": "Iraq", "MOS": "Iraq",
    "DOH": "Qatar+Saudi+Oman+Yemen ", "RIY": "Qatar+Saudi+Oman+Yemen ", "JED": "Qatar+Saudi+Oman+Yemen ", "MUS": "Qatar+Saudi+Oman+Yemen ", "SAN": "Qatar+Saudi+Oman+Yemen ",
}

def dialects_to_regions(text):
    parts = [p.strip() for p in str(text).split(",") if p.strip()]
    regions = list(dict.fromkeys(DIA_LABEL_TO_REGION[p] for p in parts if p in DIA_LABEL_TO_REGION))
    return ", ".join(regions), len(regions)

#load transliteration file
translit_df = pd.read_csv("MADAR_Lexicon_transliteration.tsv", sep="\t")
translit_df.columns = [c.strip() for c in translit_df.columns]

def split_translit(text):
    return [t.strip() for t in str(text).split(",")]

translit_df["EN_AR_list"] = translit_df["EN_ARTransliteration"].apply(split_translit)
translit_df["FR_AR_list"] = translit_df["FR_ARTransliteration"].apply(split_translit)

en_trans = dict(zip(translit_df["English Word"], translit_df["EN_AR_list"]))
fr_trans = dict(zip(translit_df["French Word"], translit_df["FR_AR_list"]))

#FSim: check if dialectal word matches any transliteration 
def compute_fsim(row):
    cod = remove_weak_letters(undiatratize(row["CODA"]))
    translits = en_trans.get(row["English"], []) + fr_trans.get(row["French"], [])
    translits = [remove_weak_letters(undiatratize(t)) for t in translits]
    return int(cod in translits and cod != "")

df["FSim"] = df.apply(compute_fsim, axis=1)

#load roots file
roots_df = pd.read_csv("roots.tsv", sep="\t")

roots_df["dia_word"] = roots_df["dia_word"].astype(str).str.strip()
roots_df["cleaned_dia_root"] = roots_df["cleaned_dia_root"].str.strip()

#map each dialectal word to its root
dia2root = roots_df.set_index("dia_word")["cleaned_dia_root"].to_dict()
df["Root"] = df["CODA"].astype(str).str.strip().map(dia2root)

#handel cases with multiple roots
def split_roots_str(root_str):
    if pd.isna(root_str):
        return []
    s = str(root_str).strip()
    if not s or s.lower() == "nan":
        return []
    return [r.strip() for r in s.split("،") if r.strip()]

#build mapping from root to set of dialects for a given concept
root_concept_to_dialects = {}

for _, row in df.dropna(subset=["Dialect"]).iterrows():
    dialect_label = row["Dialect"]
    concept_key = (row["English"], row["French"], row["MSA"])
    for r in split_roots_str(row["Root"]):
        key = (r, concept_key)
        if key not in root_concept_to_dialects:
            root_concept_to_dialects[key] = set()
        root_concept_to_dialects[key].add(dialect_label)

root_concept_dialects = pd.Series(
    {key: ", ".join(sorted(dials)) for key, dials in root_concept_to_dialects.items()}
)

#convert root dialects to regions and count
root_concept_regions = root_concept_dialects.apply(dialects_to_regions)

#group rows into one entry per dialectal word
group_cols = ["English", "French", "MSA", "POS", "CODA"]

combined = (
    df.groupby(group_cols, sort=False)
    .agg({
        "Dialect": lambda x: ", ".join(sorted(set(x.dropna()))),
        "MSA_Frequency": "first",
        "DA_Frequency": "first",
        "ASim": "first",
        "FSim": "first",
        "Root": "first"
    })
    .reset_index()
)

#DCom calculations: regions and counts for each dialect word within the same concept
regions = combined["Dialect"].apply(dialects_to_regions)
combined["DCom_Regions"] = regions.apply(lambda x: x[0])
combined["DCom"] = regions.apply(lambda x: x[1])

#RCom calculations: regions and counts for each root within the same concept
def compute_rcom(row):
    root_str = row["Root"]
    roots = split_roots_str(root_str)
    concept_key = (row["English"], row["French"], row["MSA"])

    #if there is no root, fallback to DCom count and regions
    if not roots:
        return row["DCom_Regions"], row["DCom"]

    all_regions = []
    counts = []
    for r in roots:
        key = (r, concept_key)
        region_str, cnt = root_concept_regions.get(key, ("", 0))
        counts.append(cnt)
        if region_str:
            all_regions.extend(
                [rg.strip() for rg in region_str.split(",") if rg.strip()]
            )
    unique_regions_str = ", ".join(sorted(set(all_regions))) if all_regions else ""
    avg_count = sum(counts) / len(counts) if counts else 0
    return unique_regions_str, avg_count

combined[["RCom_Regions", "RCom"]] = combined.apply(
    lambda row: pd.Series(compute_rcom(row)),
    axis=1
)

combined["Root"] = combined["Root"].fillna("")

#compute rounded of frequencies for DFreq and MSAFreq
def log_round(series):
    s = series.fillna(0)
    return s.apply(lambda x: int(round(np.log10(x))) if x > 0 else 0)

combined["DFreq"] = log_round(combined["DA_Frequency"])
combined["MSAFreq"] = log_round(combined["MSA_Frequency"])

#select final columns
final_columns = [
    "English", "French", "MSA", "POS", "Dialect",
    "DCom_Regions", "DCom",
    "CODA",
    "Root", "RCom_Regions", "RCom",
    "MSA_Frequency", "DA_Frequency",
    "MSAFreq", "DFreq",
    "ASim", "FSim"
]

combined = combined[final_columns]
combined.to_excel("MADAR_Lexicon_freq.xlsx", index=False)

print("done :)")