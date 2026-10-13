"""Algoritmos de ordenação implementados pela dupla.

Todos recebem a lista, uma função `chave` (o que comparar em cada elemento) e
`reverso` (True = do maior pro menor). Devolvem uma lista NOVA ordenada e
contam o trabalho feito num objeto Metricas, pra dar pra comparar os
algoritmos na tela de benchmark do mesmo jeito que o trabalho 1 contava
comparações na busca.

Estáveis (mantêm a ordem original entre chaves iguais): merge, insertion, radix.
Instáveis: quick, heap.

Pra tela "Corrida", o Metricas também pode gravar cada passo (comparação,
troca, movimentação) numa lista, que o navegador depois anima. Os passos
guardam o próprio elemento (não a posição), pra dar pra acompanhar cada aluno.
Fora da corrida `passos` fica None e nada é gravado.
"""

import random


class Metricas:
    def __init__(self):
        self.comparacoes = 0
        self.movimentacoes = 0  # escritas/trocas de elementos na lista
        # passos pra animação (só a corrida liga). Tipos:
        #   ("c", a, b)            comparou a com b
        #   ("t", a, b)            trocou a e b de lugar
        #   ("m", a, pos, vetor)   escreveu a na posição pos (vetor 0 = principal, 1 = auxiliar)
        #   ("v",)                 fim da passada: o auxiliar vira o principal
        #   ("l", a)               levantou a da lista (insertion)
        #   ("p", a)               a é o pivô (quick)
        self.passos = None

    def como_dict(self):
        return {"comparacoes": self.comparacoes, "movimentacoes": self.movimentacoes}


def _identidade(x):
    return x


def _vem_antes(reverso):
    """Devolve a regra "a tem que vir ANTES de b" (estritamente). Usar sempre
    a comparação estrita é o que deixa o merge e o insertion estáveis: em
    empate, nada passa na frente de ninguém."""
    if reverso:
        return lambda ka, kb: ka > kb
    return lambda ka, kb: ka < kb


# ---- merge sort (estável, O(n log n) sempre) ----

def merge_sort(lista, chave=_identidade, reverso=False, metricas=None):
    m = metricas or Metricas()
    passos = m.passos
    antes = _vem_antes(reverso)
    # calcula a chave uma vez só por elemento, e não a cada comparação
    itens = [(chave(x), x) for x in lista]
    auxiliar = itens[:]

    # versão de baixo pra cima: intercala pedaços de 1, 2, 4, 8... sem recursão
    largura = 1
    n = len(itens)
    origem, destino = itens, auxiliar
    while largura < n:
        for inicio in range(0, n, 2 * largura):
            meio = min(inicio + largura, n)
            fim = min(inicio + 2 * largura, n)
            i, j, k = inicio, meio, inicio
            while i < meio and j < fim:
                m.comparacoes += 1
                if passos is not None:
                    passos.append(("c", origem[j][1], origem[i][1]))
                # só pega da direita se ela vier ESTRITAMENTE antes; no empate
                # pega da esquerda, que é quem estava antes na lista original
                if antes(origem[j][0], origem[i][0]):
                    destino[k] = origem[j]
                    j += 1
                else:
                    destino[k] = origem[i]
                    i += 1
                if passos is not None:
                    passos.append(("m", destino[k][1], k, 1))
                k += 1
                m.movimentacoes += 1
            while i < meio:
                destino[k] = origem[i]
                if passos is not None:
                    passos.append(("m", destino[k][1], k, 1))
                i += 1
                k += 1
                m.movimentacoes += 1
            while j < fim:
                destino[k] = origem[j]
                if passos is not None:
                    passos.append(("m", destino[k][1], k, 1))
                j += 1
                k += 1
                m.movimentacoes += 1
        if passos is not None:
            passos.append(("v",))
        origem, destino = destino, origem
        largura *= 2
    return [x for _, x in origem]


# ---- quick sort (instável, O(n log n) em média) ----

def quick_sort(lista, chave=_identidade, reverso=False, metricas=None):
    """Partição em 3 vias (menores | iguais ao pivô | maiores) com pivô
    sorteado. As 3 vias evitam o pior caso quando há muita chave repetida
    (ex: ordenar por "formando", que só tem 2 valores), mas as trocas de longa
    distância embaralham quem tem chave igual - por isso ele NÃO é estável."""
    m = metricas or Metricas()
    passos = m.passos
    antes = _vem_antes(reverso)
    itens = [(chave(x), x) for x in lista]

    pilha = [(0, len(itens) - 1)]  # pilha explícita no lugar da recursão
    while pilha:
        inicio, fim = pilha.pop()
        if inicio >= fim:
            continue
        p = random.randint(inicio, fim)
        pivo = itens[p][0]
        if passos is not None:
            elemento_pivo = itens[p][1]
            passos.append(("p", elemento_pivo))
        menor, i, maior = inicio, inicio, fim
        while i <= maior:
            k = itens[i][0]
            m.comparacoes += 1
            if passos is not None:
                passos.append(("c", itens[i][1], elemento_pivo))
            if antes(k, pivo):
                if passos is not None:
                    passos.append(("t", itens[menor][1], itens[i][1]))
                itens[menor], itens[i] = itens[i], itens[menor]
                m.movimentacoes += 1
                menor += 1
                i += 1
            else:
                m.comparacoes += 1
                if passos is not None:
                    passos.append(("c", elemento_pivo, itens[i][1]))
                if antes(pivo, k):
                    if passos is not None:
                        passos.append(("t", itens[i][1], itens[maior][1]))
                    itens[i], itens[maior] = itens[maior], itens[i]
                    m.movimentacoes += 1
                    maior -= 1
                else:
                    i += 1
        pilha.append((inicio, menor - 1))
        pilha.append((maior + 1, fim))
    return [x for _, x in itens]


# ---- heap sort (instável, O(n log n) sempre, sem memória extra) ----

def heap_sort(lista, chave=_identidade, reverso=False, metricas=None):
    m = metricas or Metricas()
    passos = m.passos
    antes = _vem_antes(reverso)
    itens = [(chave(x), x) for x in lista]
    n = len(itens)

    def descer(raiz, tamanho):
        # heap de "máximo" na ordem pedida: no topo fica quem vem por último
        while True:
            filho = 2 * raiz + 1
            if filho >= tamanho:
                return
            if filho + 1 < tamanho:
                m.comparacoes += 1
                if passos is not None:
                    passos.append(("c", itens[filho][1], itens[filho + 1][1]))
                if antes(itens[filho][0], itens[filho + 1][0]):
                    filho += 1
            m.comparacoes += 1
            if passos is not None:
                passos.append(("c", itens[raiz][1], itens[filho][1]))
            if not antes(itens[raiz][0], itens[filho][0]):
                return
            if passos is not None:
                passos.append(("t", itens[raiz][1], itens[filho][1]))
            itens[raiz], itens[filho] = itens[filho], itens[raiz]
            m.movimentacoes += 1
            raiz = filho

    for raiz in range(n // 2 - 1, -1, -1):
        descer(raiz, n)
    for fim in range(n - 1, 0, -1):
        if passos is not None:
            passos.append(("t", itens[0][1], itens[fim][1]))
        itens[0], itens[fim] = itens[fim], itens[0]
        m.movimentacoes += 1
        descer(0, fim)
    return [x for _, x in itens]


# ---- insertion sort (estável, O(n²) - referência "lenta") ----

def insertion_sort(lista, chave=_identidade, reverso=False, metricas=None):
    m = metricas or Metricas()
    passos = m.passos
    antes = _vem_antes(reverso)
    itens = [(chave(x), x) for x in lista]
    for i in range(1, len(itens)):
        atual = itens[i]
        if passos is not None:
            passos.append(("l", atual[1]))
        j = i - 1
        while j >= 0:
            m.comparacoes += 1
            if passos is not None:
                passos.append(("c", atual[1], itens[j][1]))
            if not antes(atual[0], itens[j][0]):
                break
            itens[j + 1] = itens[j]
            if passos is not None:
                passos.append(("m", itens[j][1], j + 1, 0))
            m.movimentacoes += 1
            j -= 1
        itens[j + 1] = atual
        if passos is not None:
            passos.append(("m", atual[1], j + 1, 0))
        m.movimentacoes += 1
    return [x for _, x in itens]


# ---- radix sort LSD (estável, O(d·n), sem comparar elementos) ----

def radix_sort(lista, chave=_identidade, reverso=False, metricas=None, base=10):
    """Só serve pra chave inteira não negativa (matrícula, CPF, IRA x 10000...).
    Ordena dígito por dígito, do menos significativo pro mais, com um counting
    sort estável em cada passada - nenhuma comparação entre elementos."""
    m = metricas or Metricas()
    passos = m.passos
    itens = [(chave(x), x) for x in lista]
    if not itens:
        return []
    if any(not isinstance(k, int) or k < 0 for k, _ in itens):
        raise ValueError("radix sort só aceita chaves inteiras não negativas")

    maior = max(k for k, _ in itens)
    divisor = 1
    while True:
        contagem = [0] * base
        for k, _ in itens:
            contagem[(k // divisor) % base] += 1
        # posição final de cada dígito; no reverso os dígitos grandes vêm antes
        ordem_digitos = range(base - 1, -1, -1) if reverso else range(base)
        posicao = [0] * base
        acumulado = 0
        for d in ordem_digitos:
            posicao[d] = acumulado
            acumulado += contagem[d]
        saida = [None] * len(itens)
        for item in itens:  # percorre em ordem: é isso que mantém a estabilidade
            d = (item[0] // divisor) % base
            saida[posicao[d]] = item
            if passos is not None:
                passos.append(("m", item[1], posicao[d], 1))
            posicao[d] += 1
            m.movimentacoes += 1
        if passos is not None:
            passos.append(("v",))
        itens = saida
        divisor *= base
        if divisor > maior:
            break
    return [x for _, x in itens]


ALGORITMOS = {
    "merge": {"nome": "Merge sort", "funcao": merge_sort, "estavel": True, "complexidade": "O(n log n)"},
    "quick": {"nome": "Quick sort", "funcao": quick_sort, "estavel": False, "complexidade": "O(n log n) médio"},
    "heap": {"nome": "Heap sort", "funcao": heap_sort, "estavel": False, "complexidade": "O(n log n)"},
    "radix": {"nome": "Radix sort", "funcao": radix_sort, "estavel": True, "complexidade": "O(d·n)"},
    "insertion": {"nome": "Insertion sort", "funcao": insertion_sort, "estavel": True, "complexidade": "O(n²)"},
}


def ordenar(algoritmo, lista, chave=_identidade, reverso=False, metricas=None):
    return ALGORITMOS[algoritmo]["funcao"](lista, chave=chave, reverso=reverso, metricas=metricas)
