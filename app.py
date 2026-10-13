"""SIGAA Pokémon - servidor Flask.

Sobe com `py app.py` e abre em http://127.0.0.1:5000
"""

import os
import random
import threading
import time
from datetime import datetime, timedelta

from flask import Flask, abort, jsonify, render_template, request

import dados
from busca import Base
from dados import cpf_valido, eh_formando, semestre_cursando, so_digitos
from matricula import CRITERIOS, montar_candidatos, processar_turma
from ordenacao import ALGORITMOS, Metricas, merge_sort, ordenar

QTD_PADRAO = 100_000
LIMITE_BENCHMARK = 100_000
LIMITE_QUADRATICO = 10_000  # insertion sort acima disso demora demais em Python
LIMITE_CORRIDA = 40  # acima disso não cabe na tela nem dá pra acompanhar a animação

app = Flask(__name__)
trava = threading.Lock()


class Estado:
    base = None
    turmas = []
    pedidos = []
    carregado_em = 0.0


def carregar():
    inicio = time.perf_counter()
    novos_fixos = False
    if os.path.exists(dados.ARQ_ALUNOS):
        alunos = dados.carregar_alunos()
        novos_fixos = dados.garantir_fixos(alunos)
        if novos_fixos:
            dados.salvar_alunos(alunos)
    else:
        print(f"Gerando base com {QTD_PADRAO} alunos...")
        alunos = dados.gerar_alunos(QTD_PADRAO)
        dados.salvar_alunos(alunos)

    if os.path.exists(dados.ARQ_TURMAS):
        turmas = dados.carregar_turmas()
    else:
        turmas = dados.gerar_turmas()
        dados.salvar_turmas(turmas)

    if os.path.exists(dados.ARQ_PEDIDOS) and not novos_fixos:
        pedidos = dados.carregar_pedidos()
    else:
        pedidos = dados.gerar_pedidos(alunos, turmas)
        dados.salvar_pedidos(pedidos)

    Estado.base = Base(alunos)
    Estado.turmas = turmas
    Estado.pedidos = pedidos
    Estado.carregado_em = time.perf_counter() - inicio
    print(f"Base pronta: {len(alunos)} alunos, {len(turmas)} turmas, "
          f"{len(pedidos)} pedidos ({Estado.carregado_em:.1f}s)")


def turma_por_codigo(codigo):
    for t in Estado.turmas:
        if t["codigo"] == codigo:
            return t
    abort(404, "Turma não encontrada")


def pedidos_da_turma(codigo):
    return [p for p in Estado.pedidos if p["turma"] == codigo]


def aluno_json(aluno):
    return {
        **aluno,
        "semestre": semestre_cursando(aluno["matricula"]),
        "formando": eh_formando(aluno["matricula"]),
    }


def solicitacoes_do_aluno(matricula):
    """Situação do aluno em cada turma que ele pediu (processada com merge)."""
    saida = []
    for p in Estado.pedidos:
        if p["matricula"] != matricula:
            continue
        turma = turma_por_codigo(p["turma"])
        candidatos = montar_candidatos(pedidos_da_turma(turma["codigo"]), Estado.base)
        r = processar_turma(turma, candidatos, "merge")
        linha = next(x for x in r["resultado"] if x["pedido_id"] == p["id"])
        saida.append({
            "turma": turma,
            "timestamp": p["timestamp"],
            "posicao": linha["posicao"],
            "total": r["total_pedidos"],
            "deferido": linha["deferido"],
        })
    return saida


# ---- páginas ----

@app.route("/")
def pagina_busca():
    return render_template("busca.html", ativo="busca")


@app.route("/turmas")
def pagina_turmas():
    return render_template("turmas.html", ativo="turmas")


@app.route("/turmas/<codigo>")
def pagina_turma(codigo):
    turma = turma_por_codigo(codigo)
    return render_template("turma.html", ativo="turmas", turma=turma,
                           algoritmos=ALGORITMOS, criterios=CRITERIOS)


@app.route("/ranking")
def pagina_ranking():
    return render_template("ranking.html", ativo="ranking", cursos=dados.CURSOS,
                           algoritmos=ALGORITMOS)


@app.route("/benchmark")
def pagina_benchmark():
    return render_template("benchmark.html", ativo="benchmark", algoritmos=ALGORITMOS,
                           limite_quadratico=LIMITE_QUADRATICO)


@app.route("/corrida")
def pagina_corrida():
    return render_template("corrida.html", ativo="corrida", algoritmos=ALGORITMOS,
                           limite=LIMITE_CORRIDA)


# ---- API ----

@app.get("/api/info")
def api_info():
    return jsonify({
        **Estado.base.info(),
        "turmas": len(Estado.turmas),
        "pedidos": len(Estado.pedidos),
        "carregado_em": round(Estado.carregado_em, 2),
    })


@app.get("/api/alunos/exemplos")
def api_exemplos():
    fixos = [Estado.base.por_matricula(f["matricula"])[0] for f in dados.ALUNOS_FIXOS]
    alunos = [a for a in fixos if a] + random.sample(Estado.base.alunos(), 7)
    return jsonify([aluno_json(a) for a in alunos])


@app.get("/api/alunos/buscar")
def api_buscar_aluno():
    termo = request.args.get("q", "").strip()
    digitos = so_digitos(termo)
    if len(digitos) == 11:
        if not cpf_valido(digitos):
            return jsonify({"erro": "CPF inválido - confira os dígitos verificadores."}), 400
        aluno, comp_hash, comp_bin, comp_seq = Estado.base.por_cpf(digitos)
        tipo = "cpf"
    else:
        aluno, comp_bin, comp_seq = Estado.base.por_matricula(digitos)
        comp_hash = None
        tipo = "matricula"

    custo = {"hash": comp_hash, "binaria": comp_bin, "sequencial": comp_seq}
    if aluno is None:
        return jsonify({"erro": "Aluno não encontrado.", "tipo": tipo, "comparacoes": custo}), 404
    return jsonify({
        "tipo": tipo,
        "aluno": aluno_json(aluno),
        "comparacoes": custo,
        "solicitacoes": solicitacoes_do_aluno(aluno["matricula"]),
    })


@app.get("/api/turmas")
def api_turmas():
    contagem = {}
    for p in Estado.pedidos:
        contagem[p["turma"]] = contagem.get(p["turma"], 0) + 1
    return jsonify([{**t, "pedidos": contagem.get(t["codigo"], 0)} for t in Estado.turmas])


@app.get("/api/turmas/<codigo>/processar")
def api_processar(codigo):
    algoritmo = request.args.get("algoritmo", "merge")
    if algoritmo not in ALGORITMOS:
        return jsonify({"erro": "Algoritmo desconhecido."}), 400
    turma = turma_por_codigo(codigo)
    candidatos = montar_candidatos(pedidos_da_turma(codigo), Estado.base)
    inicio = time.perf_counter()
    r = processar_turma(turma, candidatos, algoritmo)
    r["tempo_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
    return jsonify(r)


@app.post("/api/pedidos")
def api_novo_pedido():
    corpo = request.get_json(force=True)
    matricula = so_digitos(str(corpo.get("matricula", "")))
    codigo = corpo.get("turma", "")
    turma = turma_por_codigo(codigo)
    aluno, _, _ = Estado.base.por_matricula(matricula)
    if aluno is None:
        return jsonify({"erro": "Matrícula não encontrada."}), 404
    with trava:
        if any(p["matricula"] == matricula and p["turma"] == codigo for p in Estado.pedidos):
            return jsonify({"erro": "Esse aluno já pediu essa turma."}), 409
        # o pedido manual entra "agora": depois de todos os pedidos do lote
        agora = datetime.now().replace(microsecond=0)
        if Estado.pedidos:
            ultimo = datetime.fromisoformat(max(p["timestamp"] for p in Estado.pedidos))
            agora = max(agora, ultimo + timedelta(seconds=1))
        pedido = {
            "id": max((p["id"] for p in Estado.pedidos), default=0) + 1,
            "matricula": matricula,
            "turma": turma["codigo"],
            "timestamp": agora.isoformat(),
        }
        Estado.pedidos.append(pedido)
        dados.salvar_pedidos(Estado.pedidos)
    return jsonify({"pedido": pedido, "aluno": aluno_json(aluno)})


@app.post("/api/pedidos/simular")
def api_simular_periodo():
    with trava:
        Estado.pedidos = dados.gerar_pedidos(Estado.base.alunos(), Estado.turmas)
        dados.salvar_pedidos(Estado.pedidos)
    return jsonify({"pedidos": len(Estado.pedidos)})


@app.post("/api/base/gerar")
def api_gerar_base():
    corpo = request.get_json(force=True)
    qtd = int(corpo.get("qtd", QTD_PADRAO))
    if not 100 <= qtd <= 1_000_000:
        return jsonify({"erro": "Escolha entre 100 e 1.000.000 alunos."}), 400
    with trava:
        inicio = time.perf_counter()
        alunos = dados.gerar_alunos(qtd)
        dados.salvar_alunos(alunos)
        Estado.base = Base(alunos)
        Estado.pedidos = dados.gerar_pedidos(alunos, Estado.turmas)
        dados.salvar_pedidos(Estado.pedidos)
        Estado.carregado_em = time.perf_counter() - inicio
    return api_info()


@app.get("/api/ranking")
def api_ranking():
    curso = request.args.get("curso", "")
    algoritmo = request.args.get("algoritmo", "heap")
    if algoritmo not in ALGORITMOS:
        return jsonify({"erro": "Algoritmo desconhecido."}), 400
    alunos = [a for a in Estado.base.alunos() if not curso or a["curso"] == curso]
    if algoritmo == "insertion" and len(alunos) > LIMITE_QUADRATICO:
        return jsonify({"erro": f"Insertion sort só até {LIMITE_QUADRATICO} alunos - "
                                f"esse filtro tem {len(alunos)}."}), 400
    m = Metricas()
    inicio = time.perf_counter()
    ordenados = ordenar(algoritmo, alunos, chave=lambda a: int(round(a["ira"] * 10000)),
                        reverso=True, metricas=m)
    tempo = time.perf_counter() - inicio
    return jsonify({
        "total": len(alunos),
        "tempo_ms": round(tempo * 1000, 2),
        "metricas": m.como_dict(),
        "top": [aluno_json(a) for a in ordenados[:50]],
    })


CHAVES_BENCHMARK = {
    "matricula": lambda a: int(a["matricula"]),
    "cpf": lambda a: int(so_digitos(a["cpf"])),
    "ira": lambda a: int(round(a["ira"] * 10000)),
}


@app.get("/api/benchmark")
def api_benchmark():
    algoritmo = request.args.get("algoritmo", "merge")
    chave_nome = request.args.get("chave", "matricula")
    ordem = request.args.get("ordem", "aleatoria")
    n = int(request.args.get("n", 1000))
    if algoritmo not in ALGORITMOS or chave_nome not in CHAVES_BENCHMARK:
        return jsonify({"erro": "Parâmetro inválido."}), 400
    if algoritmo == "insertion" and n > LIMITE_QUADRATICO:
        return jsonify({"erro": f"Insertion sort é O(n²): limitado a {LIMITE_QUADRATICO}."}), 400

    alunos = Estado.base.alunos()
    n = max(1, min(n, LIMITE_BENCHMARK, len(alunos)))
    chave = CHAVES_BENCHMARK[chave_nome]
    amostra = random.sample(alunos, n)
    if ordem != "aleatoria":
        amostra = merge_sort(amostra, chave=chave, reverso=(ordem == "decrescente"))

    m = Metricas()
    inicio = time.perf_counter()
    resultado = ordenar(algoritmo, amostra, chave=chave, metricas=m)
    tempo = time.perf_counter() - inicio
    chaves = [chave(a) for a in resultado]
    correto = all(chaves[i] <= chaves[i + 1] for i in range(len(chaves) - 1))
    return jsonify({
        "algoritmo": algoritmo,
        "nome": ALGORITMOS[algoritmo]["nome"],
        "n": n,
        "chave": chave_nome,
        "ordem": ordem,
        "tempo_ms": round(tempo * 1000, 2),
        "correto": correto,
        **m.como_dict(),
    })


# chaves com MUITO empate (semestre, IRA com 1 casa) são as que mostram a
# diferença entre estável e instável; a matrícula não empata nunca
CHAVES_CORRIDA = {
    "semestre": (lambda a: semestre_cursando(a["matricula"]), lambda v: f"{v}º"),
    "ira": (lambda a: int(round(a["ira"] * 10)), lambda v: f"{v // 10},{v % 10}"),
    "matricula": (lambda a: int(a["matricula"]), lambda v: str(v)[-4:]),
}


def passo_json(passo, indice):
    """Troca o aluno gravado no passo pela posição dele na largada."""
    tipo, *resto = passo
    if tipo == "m":
        aluno, posicao, vetor = resto
        return [tipo, indice[id(aluno)], posicao, vetor]
    return [tipo] + [indice[id(aluno)] for aluno in resto]


@app.get("/api/corrida")
def api_corrida():
    """Ordena a mesma amostra com os 5 algoritmos gravando cada passo, pra
    tela animar todos ao mesmo tempo, um passo por vez."""
    chave_nome = request.args.get("chave", "semestre")
    ordem = request.args.get("ordem", "aleatoria")
    n = int(request.args.get("n", 16))
    if chave_nome not in CHAVES_CORRIDA:
        return jsonify({"erro": "Chave inválida."}), 400
    n = max(4, min(n, LIMITE_CORRIDA))
    chave, rotulo = CHAVES_CORRIDA[chave_nome]

    largada = random.sample(Estado.base.alunos(), n)
    if ordem != "aleatoria":
        largada = merge_sort(largada, chave=chave, reverso=(ordem == "decrescente"))
    indice = {id(a): i for i, a in enumerate(largada)}

    pistas = []
    for id_alg, alg in ALGORITMOS.items():
        m = Metricas()
        m.passos = []
        ordenar(id_alg, largada, chave=chave, metricas=m)
        pistas.append({
            "algoritmo": id_alg,
            "nome": alg["nome"],
            "estavel": alg["estavel"],
            "complexidade": alg["complexidade"],
            "memoria_extra": id_alg in ("merge", "radix"),
            "passos": [passo_json(p, indice) for p in m.passos],
            **m.como_dict(),
        })
    return jsonify({
        "chave": chave_nome,
        "alunos": [{
            "nome": a["nome"],
            "matricula": a["matricula"],
            "pokemon_id": a["pokemon_id"],
            "shiny": a["shiny"],
            "valor": chave(a),
            "rotulo": rotulo(chave(a)),
        } for a in largada],
        "pistas": pistas,
    })


carregar()

if __name__ == "__main__":
    app.run(debug=False, threaded=True)
