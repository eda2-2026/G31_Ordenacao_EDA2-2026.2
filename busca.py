"""Busca sequencial indexada (kindex) + tabela hash por CPF.

Veio do trabalho 1 (G31_Busca). A diferença: os blocos agora são montados com
o merge sort da dupla (ordenacao.py) no lugar do sorted() do Python.
"""

import os
import statistics

from dados import so_digitos, CAMPOS_ALUNO
from ordenacao import merge_sort, Metricas

FATOR_ESPACO = 0.3  # 30% de cada bloco nasce vazio, reservado pra inserções futuras
FATOR_CARGA = 0.75  # ocupação máxima da tabela hash (chaves / posições disponíveis)


def tamanho_bloco_disco(caminho="."):
    try:
        return os.statvfs(caminho).f_bsize
    except AttributeError:
        import ctypes
        setores = ctypes.c_ulonglong(0)
        bytes_setor = ctypes.c_ulonglong(0)
        livres = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        raiz = os.path.splitdrive(os.path.abspath(caminho))[0] + "\\"
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceW(
            ctypes.c_wchar_p(raiz), ctypes.pointer(setores), ctypes.pointer(bytes_setor),
            ctypes.pointer(livres), ctypes.pointer(total)
        )
        return setores.value * bytes_setor.value if ok else 4096
    except OSError:
        return 4096


def registros_por_bloco(base, bloco_disco):
    media = statistics.mean(len(",".join(str(r[c]) for c in CAMPOS_ALUNO)) for r in base[:50])
    return max(1, int(bloco_disco // media))


# ---- tabela organizada (blocos com espaço vazio pra inserção futura) ----

def montar_blocos(base, capacidade, metricas=None):
    """Ordena a base por matrícula (merge sort) e divide em blocos parcialmente
    cheios - o resto fica com None, reservado pra quem chegar depois."""
    ordenada = merge_sort(base, chave=lambda r: r["matricula"], metricas=metricas)
    ocupacao = max(1, int(capacidade * (1 - FATOR_ESPACO)))

    blocos = []
    for i in range(0, len(ordenada), ocupacao):
        pedaco = ordenada[i:i + ocupacao]
        pedaco += [None] * (capacidade - len(pedaco))
        blocos.append(pedaco)
    return blocos


def montar_indice(blocos):
    # kindex: primeira matrícula de cada bloco + a posição do bloco
    return [(bloco[0]["matricula"], i) for i, bloco in enumerate(blocos)]


def extrair_base(blocos):
    return [r for bloco in blocos for r in bloco if r is not None]


def busca_binaria(indice, matricula):
    inicio, fim = 0, len(indice) - 1
    bloco = 0
    comparacoes = 0
    while inicio <= fim:
        meio = (inicio + fim) // 2
        comparacoes += 1
        if indice[meio][0] <= matricula:
            bloco = indice[meio][1]
            inicio = meio + 1
        else:
            fim = meio - 1
    return bloco, comparacoes


def busca_sequencial(bloco, matricula):
    comparacoes = 0
    for registro in bloco:
        if registro is None:
            break  # dali pra frente só tem espaço vazio
        comparacoes += 1
        if registro["matricula"] == matricula:
            return registro, comparacoes
    return None, comparacoes


def buscar(blocos, indice, matricula):
    if not indice:
        return None, 0, 0
    idx_bloco, comp_bin = busca_binaria(indice, matricula)
    registro, comp_seq = busca_sequencial(blocos[idx_bloco], matricula)
    return registro, comp_bin, comp_seq


# ---- tabela hash pela chave secundária (CPF) ----

def eh_primo(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 2
    return True


def proximo_primo(n):
    candidato = max(3, n | 1)
    while not eh_primo(candidato):
        candidato += 2
    return candidato


def hash_cpf(cpf, tamanho):
    """Horner com base 31 sobre os dígitos, módulo um tamanho primo."""
    h = 0
    for c in cpf:
        if c.isdigit():
            h = (h * 31 + (ord(c) - 48)) % tamanho
    return h


def montar_hash(base):
    """Encadeamento separado: cada posição guarda uma lista de (cpf, matrícula)."""
    tamanho = proximo_primo(int(len(base) / FATOR_CARGA) + 1)
    tabela = [None] * tamanho
    for registro in base:
        posicao = hash_cpf(registro["cpf"], tamanho)
        if tabela[posicao] is None:
            tabela[posicao] = []
        tabela[posicao].append((so_digitos(registro["cpf"]), registro["matricula"]))
    return tabela


def buscar_hash(tabela, cpf):
    posicao = hash_cpf(cpf, len(tabela))
    chave = so_digitos(cpf)
    comparacoes = 0
    for guardado, matricula in tabela[posicao] or []:
        comparacoes += 1
        if guardado == chave:
            return matricula, comparacoes
    return None, comparacoes


def buscar_por_cpf(blocos, indice, tabela, cpf):
    """CPF -> matrícula pela tabela hash, e aí matrícula -> registro pelo kindex."""
    matricula, comp_hash = buscar_hash(tabela, cpf)
    if matricula is None:
        return None, comp_hash, 0, 0
    registro, comp_bin, comp_seq = buscar(blocos, indice, matricula)
    return registro, comp_hash, comp_bin, comp_seq


def estatisticas_hash(tabela):
    tamanhos = [len(lista) for lista in tabela if lista]
    chaves = sum(tamanhos)
    return {
        "tamanho": len(tabela),
        "chaves": chaves,
        "ocupadas": len(tamanhos),
        "colisoes": chaves - len(tamanhos),
        "maior_lista": max(tamanhos) if tamanhos else 0,
        "fator_carga": round(chaves / len(tabela), 4),
    }


class Base:
    """Junta tudo que a busca precisa: blocos, kindex e hash."""

    def __init__(self, alunos):
        self.bloco_disco = tamanho_bloco_disco()
        self.capacidade = registros_por_bloco(alunos, self.bloco_disco)
        self.metricas_montagem = Metricas()
        self.blocos = montar_blocos(alunos, self.capacidade, self.metricas_montagem)
        self.indice = montar_indice(self.blocos)
        self.tabela = montar_hash(alunos)
        self.total = len(alunos)

    def por_matricula(self, matricula):
        return buscar(self.blocos, self.indice, matricula)

    def por_cpf(self, cpf):
        return buscar_por_cpf(self.blocos, self.indice, self.tabela, cpf)

    def alunos(self):
        return extrair_base(self.blocos)

    def info(self):
        return {
            "total": self.total,
            "bloco_disco": self.bloco_disco,
            "capacidade": self.capacidade,
            "blocos": len(self.blocos),
            "kindex": len(self.indice),
            "ordenacao_blocos": self.metricas_montagem.como_dict(),
            "hash": estatisticas_hash(self.tabela),
        }
