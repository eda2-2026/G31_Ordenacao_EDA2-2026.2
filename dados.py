"""Geração e persistência da base (alunos, turmas e pedidos de matrícula).

A parte de alunos/CPF veio do trabalho 1 (G31_Busca); aqui o aluno ganhou IRA
e um Pokémon, e entraram as turmas e os pedidos de matrícula.
"""

import csv
import os
import random
from datetime import datetime, timedelta

from ordenacao import merge_sort

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ARQ_ALUNOS = os.path.join(PASTA, "alunos.csv")
ARQ_TURMAS = os.path.join(PASTA, "turmas.csv")
ARQ_PEDIDOS = os.path.join(PASTA, "pedidos.csv")

CAMPOS_ALUNO = ["matricula", "nome", "cpf", "idade", "curso", "telefone", "ira", "pokemon_id", "shiny"]
CAMPOS_TURMA = ["codigo", "disciplina", "professor", "horario", "vagas"]
CAMPOS_PEDIDO = ["id", "matricula", "turma", "timestamp"]

# período letivo atual - é a partir dele que se calcula em que semestre o aluno está
ANO_ATUAL, SEMESTRE_ATUAL = 2026, 2
SEMESTRE_FORMANDO = 9  # a partir do 9º semestre o aluno conta como formando
TOTAL_POKEMON = 1025
CHANCE_SHINY = 1 / 50  # nos jogos é bem mais raro, mas aqui é pra aparecer de vez em quando

# alunos que sempre existem na base (sem CPF: ele é sorteado como o dos outros)
ALUNOS_FIXOS = [
    {
        "matricula": "222006113",
        "nome": "João Marcos Moraes de Andrade",
        "idade": 22,
        "curso": "Engenharia de Software",
        "telefone": "(61) 90000-0000",
        "ira": 4.2,
        "pokemon_id": 133,  # Eevee
        "shiny": 1,
        "turmas": ["FGA0030", "FGA0124"],  # sempre pede essas no período de matrícula
    },
]

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Hugo",
         "Isabela", "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olivia",
         "Pedro", "Rafael", "Sofia", "Thiago", "Victor", "Ash", "Misty", "Brock"]
SOBRENOMES = ["Silva", "Costa", "Souza", "Alves", "Lima", "Dias", "Martins",
              "Rocha", "Pereira", "Nunes", "Gomes", "Barros", "Teixeira", "Ketchum"]
CURSOS = ["Ciência da Computação", "Engenharia de Software", "Engenharia Elétrica",
          "Direito", "Medicina", "Administração", "Psicologia", "Física",
          "Matemática", "Design", "Economia"]

DISCIPLINAS = [
    ("FGA0030", "Estruturas de Dados 2", "Prof. Carvalho"),
    ("FGA0003", "Compiladores 1", "Prof. Elm"),
    ("FGA0124", "Projeto de Algoritmos", "Prof. Birch"),
    ("FGA0137", "Sistemas de Banco de Dados 1", "Prof. Rowan"),
    ("FGA0170", "Interação Humano-Computador", "Profa. Juniper"),
    ("FGA0172", "Engenharia de Requisitos", "Prof. Sycamore"),
    ("FGA0208", "Arquitetura e Desenho de Software", "Prof. Kukui"),
    ("FGA0242", "Técnicas de Programação em Plataformas Emergentes", "Profa. Magnolia"),
    ("FGA0161", "Cálculo 1", "Profa. Ivy"),
    ("FGA0162", "Probabilidade e Estatística", "Prof. Willow"),
    ("FGA0071", "Física 1", "Profa. Sada"),
    ("FGA0313", "Orientação a Objetos", "Prof. Turo"),
    ("FGA0314", "Testes de Software", "Prof. Carvalho"),
    ("FGA0315", "Qualidade de Software 1", "Prof. Elm"),
    ("FGA0316", "Fundamentos de Redes de Computadores", "Profa. Juniper"),
    ("FGA0317", "Sistemas Operacionais", "Prof. Kukui"),
]
HORARIOS = ["24M12", "35M34", "24T23", "35T45", "246N12", "35M12", "24T45", "6M1234"]


# ---- matrícula e semestre ----

def gerar_matricula(ano, semestre, sequencial):
    aa = str(ano)[-2:].zfill(2)
    seq = str(sequencial).zfill(5)
    return f"{aa}{semestre}0{seq}"


def semestre_cursando(matricula):
    """A matrícula começa com ano (2 dígitos) + semestre de ingresso, então dá
    pra saber em que semestre o aluno está sem guardar isso em lugar nenhum."""
    ano = 2000 + int(matricula[:2])
    sem = int(matricula[2])
    return (ANO_ATUAL - ano) * 2 + (SEMESTRE_ATUAL - sem) + 1


def eh_formando(matricula):
    return semestre_cursando(matricula) >= SEMESTRE_FORMANDO


# ---- CPF: a chave secundária da base (igual ao trabalho 1) ----

def so_digitos(texto):
    return "".join(c for c in texto if c.isdigit())


def formatar_cpf(digitos):
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def digito_verificador(digitos, peso_inicial):
    soma = sum(int(d) * peso for d, peso in zip(digitos, range(peso_inicial, 1, -1)))
    resto = (soma * 10) % 11
    return 0 if resto == 10 else resto


def cpf_valido(cpf):
    digitos = so_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    d1 = digito_verificador(digitos[:9], 10)
    d2 = digito_verificador(digitos[:9] + str(d1), 11)
    return digitos[9:] == f"{d1}{d2}"


def gerar_cpf(usados):
    while True:
        nove = str(random.randint(0, 999_999_999)).zfill(9)
        d1 = digito_verificador(nove, 10)
        d2 = digito_verificador(nove + str(d1), 11)
        digitos = f"{nove}{d1}{d2}"
        if digitos not in usados:
            usados.add(digitos)
            return formatar_cpf(digitos)


def gerar_ira():
    # a maioria fica no meio, pouca gente perto de 0 ou de 5; sorteia de novo
    # se sair da faixa (cortar em 5 deixaria muita gente empatada com 5,0000)
    while True:
        ira = random.gauss(3.2, 0.9)
        if 0.0 <= ira <= 5.0:
            return round(ira, 4)


# ---- alunos ----

def gerar_alunos(qtd, ano_inicio=2021):
    periodos = [(ano, sem) for ano in range(ano_inicio, ANO_ATUAL + 1) for sem in (1, 2)
                if (ano, sem) <= (ANO_ATUAL, SEMESTRE_ATUAL)]
    contador = {}
    cpfs_usados = set()
    fixas = {a["matricula"] for a in ALUNOS_FIXOS}
    base = [_aluno_fixo(a, cpfs_usados) for a in ALUNOS_FIXOS]
    while len(base) < qtd:
        ano, semestre = random.choice(periodos)
        contador[(ano, semestre)] = contador.get((ano, semestre), 0) + 1
        matricula = gerar_matricula(ano, semestre, contador[(ano, semestre)])
        if matricula in fixas:
            continue  # essa matrícula já é de um aluno fixo
        base.append({
            "matricula": matricula,
            "nome": f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}",
            "cpf": gerar_cpf(cpfs_usados),
            "idade": random.randint(17, 35),
            "curso": random.choice(CURSOS),
            "telefone": f"(61) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            "ira": gerar_ira(),
            "pokemon_id": random.randint(1, TOTAL_POKEMON),
            "shiny": int(random.random() < CHANCE_SHINY),
        })
    random.shuffle(base)
    return base


def _aluno_fixo(fixo, cpfs_usados):
    aluno = {c: fixo[c] for c in CAMPOS_ALUNO if c in fixo}
    aluno["cpf"] = gerar_cpf(cpfs_usados)
    return aluno


def garantir_fixos(base):
    """Bases salvas antes dos alunos fixos existirem: coloca eles no lugar de
    quem estiver com a mesma matrícula. Devolve True se a base mudou."""
    faltando = [f for f in ALUNOS_FIXOS
                if not any(r["matricula"] == f["matricula"] and r["nome"] == f["nome"] for r in base)]
    if not faltando:
        return False
    fixas = {f["matricula"] for f in faltando}
    base[:] = [r for r in base if r["matricula"] not in fixas]
    usados = {so_digitos(r["cpf"]) for r in base}
    base.extend(_aluno_fixo(f, usados) for f in faltando)
    return True


def _salvar(caminho, campos, linhas):
    os.makedirs(PASTA, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as arq:
        escritor = csv.DictWriter(arq, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def _carregar(caminho):
    with open(caminho, "r", newline="", encoding="utf-8") as arq:
        return list(csv.DictReader(arq))


def salvar_alunos(base):
    _salvar(ARQ_ALUNOS, CAMPOS_ALUNO, base)


def carregar_alunos():
    base = _carregar(ARQ_ALUNOS)
    for r in base:
        r["idade"] = int(r["idade"])
        r["ira"] = float(r["ira"])
        r["pokemon_id"] = int(r["pokemon_id"])
        r["shiny"] = int(r.get("shiny") or 0)  # CSVs antigos não têm a coluna
    return base


# ---- turmas e pedidos de matrícula ----

def gerar_turmas():
    turmas = []
    for codigo, disciplina, professor in DISCIPLINAS:
        turmas.append({
            "codigo": codigo,
            "disciplina": disciplina,
            "professor": professor,
            "horario": random.choice(HORARIOS),
            "vagas": random.choice([25, 30, 40, 45, 50, 60]),
        })
    return turmas


def salvar_turmas(turmas):
    _salvar(ARQ_TURMAS, CAMPOS_TURMA, turmas)


def carregar_turmas():
    turmas = _carregar(ARQ_TURMAS)
    for t in turmas:
        t["vagas"] = int(t["vagas"])
    return turmas


def inicio_periodo_matricula():
    return datetime(ANO_ATUAL, 7 if SEMESTRE_ATUAL == 2 else 2, 20, 8, 0, 0)


def gerar_pedidos(alunos, turmas, proximo_id=1, fator=(1.4, 3.0)):
    """Simula o período de matrícula: cada turma recebe mais pedidos do que
    vagas (entre 1,4x e 3x), de alunos sorteados, em horários espalhados por
    3 dias. Cada pedido tem um timestamp único - é o último critério de
    desempate, então não pode haver dois iguais."""
    inicio = inicio_periodo_matricula()
    pedidos = []
    usados = set()
    fixas = {a["matricula"] for a in ALUNOS_FIXOS}
    for turma in turmas:
        qtd = int(turma["vagas"] * random.uniform(*fator))
        escolhidos = [a for a in random.sample(alunos, qtd) if a["matricula"] not in fixas]
        escolhidos += [a for a in ALUNOS_FIXOS if turma["codigo"] in a["turmas"]]
        for aluno in escolhidos:
            segundos = random.randint(0, 3 * 24 * 3600)
            while segundos in usados:
                segundos += 1
            usados.add(segundos)
            pedidos.append({
                "matricula": aluno["matricula"],
                "turma": turma["codigo"],
                "timestamp": (inicio + timedelta(seconds=segundos)).isoformat(),
            })
    # os ids seguem a ordem de chegada, como num sistema de verdade
    pedidos = merge_sort(pedidos, chave=lambda p: p["timestamp"])
    for i, p in enumerate(pedidos):
        p["id"] = proximo_id + i
    return pedidos


def salvar_pedidos(pedidos):
    _salvar(ARQ_PEDIDOS, CAMPOS_PEDIDO, pedidos)


def carregar_pedidos():
    pedidos = _carregar(ARQ_PEDIDOS)
    for p in pedidos:
        p["id"] = int(p["id"])
    return pedidos
