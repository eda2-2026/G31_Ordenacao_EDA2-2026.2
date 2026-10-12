"""Processamento de matrícula: quem fica com as vagas de uma turma.

Regra de prioridade (da mais importante pra menos):
  1. formando primeiro
  2. maior IRA
  3. semestre mais avançado
  4. pedido feito mais cedo

Em vez de um comparador com as 4 regras juntas, a ordenação é feita em 4
passadas, da regra MENOS importante pra MAIS importante. Isso só dá certo se
o algoritmo for ESTÁVEL: na passada do IRA, por exemplo, dois alunos com o
mesmo IRA têm que continuar na ordem que a passada do semestre deixou. Com
merge/radix/insertion o resultado sai certo; com quick/heap os empates se
embaralham e alunos com a mesma prioridade trocam de lugar - às vezes
atravessando a linha de corte das vagas.
"""

from datetime import datetime

from ordenacao import ALGORITMOS, Metricas, ordenar
from dados import semestre_cursando, eh_formando

# (campo, rótulo, decrescente?) - do mais importante pro menos importante
CRITERIOS = [
    ("formando", "Formando", True),
    ("ira_int", "IRA", True),
    ("semestre", "Semestre", True),
    ("chegada", "Hora do pedido", False),
]


def montar_candidatos(pedidos, base):
    """Junta cada pedido com os dados do aluno, buscando pelo kindex do trabalho 1.
    Todas as chaves viram inteiros não negativos pra o radix sort também funcionar."""
    candidatos = []
    for pedido in pedidos:
        aluno, _, _ = base.por_matricula(pedido["matricula"])
        if aluno is None:
            continue  # aluno removido da base depois do pedido
        chegada = datetime.fromisoformat(pedido["timestamp"])
        candidatos.append({
            "pedido_id": pedido["id"],
            "matricula": aluno["matricula"],
            "nome": aluno["nome"],
            "curso": aluno["curso"],
            "pokemon_id": aluno["pokemon_id"],
            "shiny": aluno["shiny"],
            "ira": aluno["ira"],
            "ira_int": int(round(aluno["ira"] * 10000)),
            "semestre": semestre_cursando(aluno["matricula"]),
            "formando": int(eh_formando(aluno["matricula"])),
            "timestamp": pedido["timestamp"],
            "chegada": int(chegada.timestamp()),
        })
    return candidatos


def ordenar_por_prioridade(candidatos, algoritmo):
    """Uma passada por critério, do menos importante pro mais importante."""
    total = Metricas()
    passadas = []
    lista = candidatos
    for campo, rotulo, decrescente in reversed(CRITERIOS):
        m = Metricas()
        lista = ordenar(algoritmo, lista, chave=lambda c, campo=campo: c[campo],
                        reverso=decrescente, metricas=m)
        passadas.append({"criterio": rotulo, **m.como_dict()})
        total.comparacoes += m.comparacoes
        total.movimentacoes += m.movimentacoes
    return lista, total, passadas


def processar_turma(turma, candidatos, algoritmo="merge"):
    ordenados, metricas, passadas = ordenar_por_prioridade(candidatos, algoritmo)

    # o merge (estável) é a resposta certa; se o escolhido for outro, compara
    if algoritmo == "merge":
        correta = ordenados
    else:
        correta, _, _ = ordenar_por_prioridade(candidatos, "merge")
    posicao_correta = {c["pedido_id"]: i for i, c in enumerate(correta)}

    vagas = turma["vagas"]
    resultado = []
    divergentes = 0
    injusticas = 0  # quem ganhou ou perdeu vaga por causa da instabilidade
    for i, c in enumerate(ordenados):
        certo = posicao_correta[c["pedido_id"]]
        deferido = i < vagas
        deveria = certo < vagas
        if certo != i:
            divergentes += 1
        if deferido != deveria:
            injusticas += 1
        resultado.append({
            **c,
            "posicao": i + 1,
            "posicao_correta": certo + 1,
            "deferido": deferido,
            "deveria_deferir": deveria,
        })

    return {
        "turma": turma,
        "algoritmo": algoritmo,
        "algoritmo_nome": ALGORITMOS[algoritmo]["nome"],
        "estavel": ALGORITMOS[algoritmo]["estavel"],
        "total_pedidos": len(candidatos),
        "deferidos": min(vagas, len(candidatos)),
        "divergentes": divergentes,
        "injusticas": injusticas,
        "metricas": metricas.como_dict(),
        "passadas": passadas,
        "resultado": resultado,
    }
