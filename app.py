import csv
import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "trocar-esta-chave")

# Arquivos de dados
DADOS_CRE_FILE = "dados_cre.csv"
MUNICIPIOS_CRE_FILE = "municipios_por_cre.csv"

# Lista oficial de CREs (37) - nomes como na SED/ACT
CRE_LIST = [
    "CRE Araranguá",
    "CRE Blumenau",
    "CRE Braço do Norte",
    "CRE Brusque",
    "CRE Caçador",
    "CRE Campos Novos",
    "CRE Canoinhas",
    "CRE Chapecó",
    "CRE Concórdia",
    "CRE Criciúma",
    "CRE Curitibanos",
    "CRE Dionísio Cerqueira",
    "CRE Florianópolis",
    "CRE Ibirama",
    "CRE Itajaí",
    "CRE Itapiranga",
    "CRE Ituporanga",
    "CRE Jaraguá do Sul",
    "CRE Joaçaba",
    "CRE Joinville",
    "CRE Lages",
    "CRE Laguna",
    "CRE Mafra",
    "CRE Maravilha",
    "CRE Palmitos",
    "CRE Quilombo",
    "CRE Rio do Sul",
    "CRE São Bento do Sul",
    "CRE São Joaquim",
    "CRE São Lourenço do Oeste",
    "CRE São Miguel do Oeste",
    "CRE Seara",
    "CRE Taió",
    "CRE Timbó",
    "CRE Tubarão",
    "CRE Videira",
    "CRE Xanxerê",
]

# Tons de verde do Governo de SC
GOV_GREENS = ["#A6CE39", "#3DB44A"]


def ensure_dados_cre_file():
    """Garante que o CSV de dados das CREs exista com todas as CREs zeradas."""
    if os.path.exists(DADOS_CRE_FILE):
        return

    headers = [
        "CRE",
        "Publico_EE",
        "Num_Escolas",
        "Num_Escolas_AEE",
        "Estudantes_AEE",
        "Participantes",
        "Assessorias_Presenciais",
        "Assessorias_Online",
    ]
    with open(DADOS_CRE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        for cre in CRE_LIST:
            writer.writerow([cre, 0, 0, 0, 0, 0, 0, 0])


def load_cre_base():
    """Carrega os dados brutos do CSV (sem indicadores derivados)."""
    ensure_dados_cre_file()
    base = {}
    with open(DADOS_CRE_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cre = row["CRE"].strip()
            if not cre:
                continue

            def to_int(value):
                try:
                    return int(str(value).strip() or "0")
                except Exception:
                    return 0

            base[cre] = {
                "CRE": cre,
                "Publico_EE": to_int(row.get("Publico_EE", 0)),
                "Num_Escolas": to_int(row.get("Num_Escolas", 0)),
                "Num_Escolas_AEE": to_int(row.get("Num_Escolas_AEE", 0)),
                "Estudantes_AEE": to_int(row.get("Estudantes_AEE", 0)),
                "Participantes": to_int(row.get("Participantes", 0)),
                "Assessorias_Presenciais": to_int(row.get("Assessorias_Presenciais", 0)),
                "Assessorias_Online": to_int(row.get("Assessorias_Online", 0)),
            }
    # Garante que toda CRE da lista esteja presente
    for cre in CRE_LIST:
        if cre not in base:
            base[cre] = {
                "CRE": cre,
                "Publico_EE": 0,
                "Num_Escolas": 0,
                "Num_Escolas_AEE": 0,
                "Estudantes_AEE": 0,
                "Participantes": 0,
                "Assessorias_Presenciais": 0,
                "Assessorias_Online": 0,
            }
    return base


def compute_cre_with_indicators():
    """
    Retorna dict com dados por CRE já com indicadores derivados:
    - estudantes_fora_aee, perc_fora_aee
    - escolas_sem_aee, perc_escolas_sem_aee
    - total_assessorias
    """
    base = load_cre_base()
    enriched = {}

    for cre, row in base.items():
        publico = row["Publico_EE"]
        escolas = row["Num_Escolas"]
        escolas_aee = row["Num_Escolas_AEE"]
        est_aee = row["Estudantes_AEE"]
        participantes = row["Participantes"]
        ass_pres = row["Assessorias_Presenciais"]
        ass_on = row["Assessorias_Online"]

        estudantes_fora = max(publico - est_aee, 0)
        perc_fora = (estudantes_fora / publico * 100) if publico > 0 else 0.0

        escolas_sem_aee = max(escolas - escolas_aee, 0)
        perc_escolas_sem = (escolas_sem_aee / escolas * 100) if escolas > 0 else 0.0

        total_ass = ass_pres + ass_on

        enriched[cre] = {
            "cre": cre,
            "publico_ee": publico,
            "num_escolas": escolas,
            "num_escolas_aee": escolas_aee,
            "estudantes_aee": est_aee,
            "estudantes_fora_aee": estudantes_fora,
            "perc_fora_aee": perc_fora,
            "escolas_sem_aee": escolas_sem_aee,
            "perc_escolas_sem_aee": perc_escolas_sem,
            "participantes": participantes,
            "assessorias_presenciais": ass_pres,
            "assessorias_online": ass_on,
            "total_assessorias": total_ass,
        }

    return enriched


def compute_totals(cre_data):
    """Soma geral (todas as CREs) com indicadores derivados."""
    totals = {
        "publico_ee": 0,
        "num_escolas": 0,
        "num_escolas_aee": 0,
        "estudantes_aee": 0,
        "participantes": 0,
        "assessorias_presenciais": 0,
        "assessorias_online": 0,
    }

    for d in cre_data.values():
        totals["publico_ee"] += d["publico_ee"]
        totals["num_escolas"] += d["num_escolas"]
        totals["num_escolas_aee"] += d["num_escolas_aee"]
        totals["estudantes_aee"] += d["estudantes_aee"]
        totals["participantes"] += d["participantes"]
        totals["assessorias_presenciais"] += d["assessorias_presenciais"]
        totals["assessorias_online"] += d["assessorias_online"]

    # Indicadores derivados globais
    estudantes_fora = max(totals["publico_ee"] - totals["estudantes_aee"], 0)
    perc_fora = (
        estudantes_fora / totals["publico_ee"] * 100 if totals["publico_ee"] > 0 else 0.0
    )

    escolas_sem_aee = max(
        totals["num_escolas"] - totals["num_escolas_aee"], 0
    )
    perc_escolas_sem = (
        escolas_sem_aee / totals["num_escolas"] * 100
        if totals["num_escolas"] > 0
        else 0.0
    )

    total_ass = totals["assessorias_presenciais"] + totals["assessorias_online"]

    totals["estudantes_fora_aee"] = estudantes_fora
    totals["perc_fora_aee"] = perc_fora
    totals["escolas_sem_aee"] = escolas_sem_aee
    totals["perc_escolas_sem_aee"] = perc_escolas_sem
    totals["total_assessorias"] = total_ass

    return totals


def load_municipios_cre():
    """
    Lê CSV municipio -> CRE.
    Estrutura esperada: Municipio;CRE
    Retorna dict { NOME_MUNÍCIPIO_MAIÚSCULO: "CRE XXX" }
    """
    mapping = {}
    if not os.path.exists(MUNICIPIOS_CRE_FILE):
        return mapping

    with open(MUNICIPIOS_CRE_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            mun = (row.get("Municipio") or "").strip()
            cre = (row.get("CRE") or "").strip()
            if not mun or not cre:
                continue
            mapping[mun.upper()] = cre
    return mapping


@app.route("/")
def painel():
    cre_data = compute_cre_with_indicators()
    totals = compute_totals(cre_data)
    municipios_cre = load_municipios_cre()

    return render_template(
        "painel.html",
        cre_data_json=json.dumps(cre_data, ensure_ascii=False),
        totals_json=json.dumps(totals, ensure_ascii=False),
        municipios_cre_json=json.dumps(municipios_cre, ensure_ascii=False),
        gov_greens_json=json.dumps(GOV_GREENS),
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    ensure_dados_cre_file()

    if request.method == "POST":
        try:
            total_rows = int(request.form.get("total_rows", "0"))
        except Exception:
            total_rows = 0

        rows = []
        for i in range(total_rows):
            cre = request.form.get(f"cre_{i}", "").strip()
            if not cre:
                continue

            def to_int_field(name):
                raw = request.form.get(f"{name}_{i}", "").strip()
                try:
                    return int(raw or "0")
                except Exception:
                    return 0

            row = {
                "CRE": cre,
                "Publico_EE": to_int_field("publico_ee"),
                "Num_Escolas": to_int_field("num_escolas"),
                "Num_Escolas_AEE": to_int_field("num_escolas_aee"),
                "Estudantes_AEE": to_int_field("estudantes_aee"),
                "Participantes": to_int_field("participantes"),
                "Assessorias_Presenciais": to_int_field("ass_pres"),
                "Assessorias_Online": to_int_field("ass_on"),
            }
            rows.append(row)

        # Garante que todas CRE_LIST estão presentes (caso falte alguma)
        existing_cres = {r["CRE"] for r in rows}
        for cre in CRE_LIST:
            if cre not in existing_cres:
                rows.append(
                    {
                        "CRE": cre,
                        "Publico_EE": 0,
                        "Num_Escolas": 0,
                        "Num_Escolas_AEE": 0,
                        "Estudantes_AEE": 0,
                        "Participantes": 0,
                        "Assessorias_Presenciais": 0,
                        "Assessorias_Online": 0,
                    }
                )

        # Grava CSV
        headers = [
            "CRE",
            "Publico_EE",
            "Num_Escolas",
            "Num_Escolas_AEE",
            "Estudantes_AEE",
            "Participantes",
            "Assessorias_Presenciais",
            "Assessorias_Online",
        ]
        with open(DADOS_CRE_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=";")
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

        flash("Dados salvos com sucesso.", "success")
        return redirect(url_for("admin"))

    # GET
    base = load_cre_base()
    # Garante ordenação conforme CRE_LIST
    ordered_rows = [base[cre] for cre in CRE_LIST]

    return render_template(
        "admin.html",
        cre_rows=ordered_rows,
        total_rows=len(ordered_rows),
    )


if __name__ == "__main__":
    # Para desenvolvimento local
    app.run(debug=True)
