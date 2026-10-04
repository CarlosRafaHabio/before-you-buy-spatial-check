# Before You Buy Spatial Check — V0

Núcleo determinístico independente para a pergunta: **com os dados fornecidos, o footprint
retangular deste móvel, nesta posição e rotação explícitas, viola o envelope ou as
restrições retangulares informadas?**

Python 3.12+, biblioteca padrão, sem dependências, rede, modelos, banco ou frontend.
Engine version: `0.3.0` (ciclo de hardening). Geometria V0 preservada.
**Licença: [Apache-2.0](LICENSE). Copyright (c) 2026 Carlos Rafael.**

Distribuição de fontes em preparação; API V0 experimental, sem promessa de
compatibilidade entre versões. O núcleo é independente de qualquer plataforma.
Capafy é somente um consumidor futuro possível; não há dependência ou integração
Capafy implementada. Outros projetos podem assumir o papel de host.

## Usar a distribuição de fontes

Requer Python 3.12+. Não há dependências externas a instalar. Abra um terminal na
raiz desta árvore, onde estão `spatial_check/`, `schemas/` e `examples/`; os imports
funcionam a partir dessa raiz. Não existe pacote publicado, `pip install` suportado,
build configurado ou distribuição PyPI neste candidato.

Para consumir em outro projeto, disponibilize a pasta `spatial_check/` no caminho
de imports desse projeto, respeitando a licença Apache-2.0. Consumidores que usam os
schemas devem disponibilizar também `schemas/`. Packaging será uma decisão separada.

As obrigações do host estão em `HOST_GUIDE.md`; a superfície suportada está em
`PUBLIC_API.md`. `TESTS.md` separa regressão do core, Consumer Contract e Host Harness.
O milestone atual registra 218 testes aprovados; `TEST_REPORT.md` conserva os
milestones anteriores. Testes aprovados não certificam plataforma, medida ou compra.

## Executar

No diretório deste projeto:

```sh
python -m unittest discover -s tests -v
python -m spatial_check --demo fits
python -m spatial_check --demo clearance_conflict --text
```

CLI: saída JSON por padrão; `--text` usa apresentação determinística. Códigos de saída:
0 = nenhum conflito nos dados fornecidos, 1 = conflito demonstrado, 2 = não verificado
ou entrada inválida. Não interprete apenas a ausência de exceção como aprovação.

## Why?

LLMs podem extrair e explicar informações espaciais; interpretação não equivale a
validação geométrica. Nenhum campo `source`, `verified` ou frase de confirmação
fornecido pelo modelo cria autoridade neste motor.

## Architecture

Input → claim estruturada → confirmação explícita pelo host → evidência opaca →
geometria determinística → resultado.

O parser só produz dados. `claim_from_data()` produz uma `EvidenceClaim`, ainda sem
confiança. `HostIntake.confirm()` é uma capacidade reservada ao código confiável do
host, após revisão externa, e emite `TrustedEvidence`. Só esse recibo pode entrar no
engine; dicionários livres são recusados. Veja `TRUST_BOUNDARY.md`.

Exemplo executável **somente com fixtures sintéticas incluídas**. A chamada de
confirmação abaixo simula revisão externa para demonstrar a API; não confirma pessoa,
fabricante ou ambiente real. Em integração real, o host deve revisar o payload exato
por canal independente antes de chamar `confirm`; não adaptar este exemplo para
confirmar automaticamente arquivos arbitrários ou respostas do modelo.

```python
import json
from pathlib import Path
from uuid import uuid4

from spatial_check import evaluate
from spatial_check.json_io import load
from spatial_check.trust import HostIntake, LifecycleRegistry, claim_from_data

request = load(Path("examples/fits.request.json"))
candidate_data = load(Path("examples/fits.evidence.json"))
# Identidade do caso gerada pelo host, antes de congelar e revisar a claim.
case_id = str(uuid4())
request["case_id"] = candidate_data["case_id"] = case_id
authority = LifecycleRegistry()  # uma autoridade volátil por domínio
host = HostIntake(authority)  # outros hosts do mesmo domínio recebem o MESMO objeto
claim = claim_from_data(candidate_data)  # ainda NÃO é evidência confiável
# Somente este exemplo sintético: escopo conhecido da fixture, selecionado pelo host.
# Revisão real deve incidir sobre claim.payload e anteceder a emissão.
receipt = host.confirm(
    claim, case_id=case_id, revision="r1", room_identity="room-1",
    item_identity="product-1", confirmation_ref="synthetic-example-review"
)
result = evaluate(request, receipt)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

O exemplo chama a API de host e pode reportar `HOST_CONFIRMED_INPUT`; esse modo
descreve a emissão, não autenticidade nem verdade. O caso permanece sintético.
Para demonstração pelo CLI, prefira `--demo`, que informa `DEMO_ONLY`.

A confirmação não é inferida por texto, JSON ou `source.kind`. Esta biblioteca não
autentica usuários nem fabricantes: o host deve obter e verificar o evento real.
Não exponha `HostIntake`, `confirm` ou execução Python como ferramentas do LLM.
Recibos não são serializáveis, copiáveis ou criáveis por JSON. Não há segredo ou login.
Esta separação protege o canal de dados; não é sandbox contra código Python hostil
no mesmo processo. `confirmation_ref` serve para rastreio, não como senha ou prova
criptográfica. Pode se repetir e não é receipt ID. `result["admission"]` identifica
o recibo emitido e seu domínio, além do evento, escopo e digest da evidência.
Um host que confirme automaticamente qualquer claim rompe o contrato.

### CLI e exemplos

`--demo` aceita apenas os três nomes fixos, sem arquivos externos. A saída tem
`execution_mode=DEMO_ONLY`; dados sintéticos não representam confirmação de pessoa
ou fabricante. Nenhum resultado de demonstração deve ser aplicado a uma compra real.

O comando legado com dois arquivos continua disponível para inspecionar a fronteira:

```sh
python -m spatial_check examples/fits.request.json examples/fits.evidence.json
```

Ele retorna `UNVERIFIED`, `TRUST_REQUIRED`, exit code 2: ler um arquivo não confirma
seus dados. **Não existe flag de auto-confirmação nem importação de recibo de JSON.**
A integração real precisa chamar a API de host separada, como no exemplo acima.

## Estados e precedência

| Estado público exato | Significado |
| --- | --- |
| `CONFLICT DETECTED` | Dados suficientes para os testes solicitados; pelo menos uma violação demonstrada. |
| `NO CONFLICT DETECTED IN PROVIDED DATA` | Todos os testes aplicáveis executados com evidência suficiente e nenhuma violação detectada. |
| `UNVERIFIED` | Entrada inválida, dado ausente, fonte conflitante/inadmissível ou teste bloqueado. |

Precedência: bloqueio → `UNVERIFIED`; sem bloqueio e com achado → `CONFLICT DETECTED`;
sem ambos → `NO CONFLICT DETECTED IN PROVIDED DATA`. Se uma violação independente
for demonstrada junto de uma pendência, ela permanece em `findings`, com estado geral
`UNVERIFIED`. Os checks individuais continuam `PASS`, `CONFLICT` ou `BLOCKED`.
Não há enum público `VALID`, certificado, pontuação de segurança ou recomendação de compra.

## Geometria exata e escopo

- Envelope do ambiente: retângulo útil de `(0,0)` a `(width,depth)` em cm.
- X cresce para a direita e Y para baixo numa planta abstrata. Não há correspondência
  automática com uma foto, norte ou orientação real do imóvel.
- Posição do móvel: canto mínimo X/Y do bounding box **já rotacionado**, nunca centro.
- Rotações explícitas: 0, 90, 180, 270 graus; 90/270 trocam width/depth. A posição não
  muda e nenhuma dimensão é reduzida. Ausência de rotação é pendência, não zero implícito.
- Containment inclui bordas; interseção exige área positiva. Encostar é permitido
  apenas no modelo matemático, sem garantia de tolerância de montagem real.
- `openings` são **reservas retangulares fornecidas** para aberturas, não linhas de vão,
  arcos de porta, estimativas de giro ou portas de tamanho padrão. Nenhuma reserva é
  calculada automaticamente. `explicit_exclusions` são áreas retangulares a evitar.
- Verifica móvel contra cada reserva. Duas reservas podem se sobrepor legitimamente;
  não são tratadas como dois móveis. V0 avalia um móvel e não cenas multimóvel completas.
- Reservas podem cruzar o limite do ambiente (por exemplo, abrangendo uma abertura).
  Isso não expande o ambiente, não implica clipping e não cria novo espaço útil.

Clearance é **distância livre direcional do footprint**, em `left/right/top/bottom`
nos eixos globais, até a parede ou reserva mais próxima que tenha sobreposição
transversal positiva com a face inteira do móvel. Requisito é sempre explícito.
Os lados não giram junto com o móvel: o chamador precisa indicar o lado global correto.
Não é uma medida de percurso humano, largura mínima de circulação ou acessibilidade.

Interseção existente com reserva limita o clearance a zero (ou mantém distância
negativa se já houver extrapolação da parede). Equality `actual >= required` passa.
Requisito zero é permitido quando fornecido; requisito negativo é inválido.
Não informado = nenhum teste de clearance e nenhuma garantia sobre operação do móvel.

## Números e unidades

- Interno: `Decimal` em centímetros com contexto isolado, sem tolerância epsilon.
- Entrada: inteiros JSON ou strings decimais; decimais JSON de ponto flutuante são
  recusados. Use `"3.20"` ou `"3,20"`, com unidade `m`, `cm` ou `mm`.
- Vírgula e ponto são separadores decimais, **nunca de milhares**. Sem agrupamento,
  espaços, expoentes, `NaN`, `Infinity`, bool ou inferência de unidade.
- A exceção de segurança é um único separador seguido de três algarismos, com
  prefixo não zero de 1–3 algarismos: `"1.200"`, `"1,200"`, `"12.345"`, inclusive
  negativos e prefixos com zeros, são ambíguos e recusados por `confirm()` antes
  de emitir recibo. Não são convertidos nem para 1200 nem para 1.2.
  O host deve esclarecer o significado e submeter uma nova claim: `"1200"` para
  mil e duzentos, ou `"1.2"`/`"1,2"` para um vírgula dois. Não remova zeros de
  uma entrada ambígua automaticamente. A claim original e o erro preservam o token.
- `"3.20"`, `"3,20"`, `"1.2"`, `"1,2"`, `"0.001"` e `"0.000001"` continuam
  decimais explícitos aceitos. Não existe mínimo arquitetônico de dimensão.
  Uma claim recusada permanece não confiável; `evaluate` retorna UNVERIFIED
  sem recibo. O parser numérico também bloqueia a ambiguidade como defesa adicional.
- Máximo 12 algarismos inteiros e 6 casas decimais na entrada; magnitude após conversão
  limitada a 1.000.000 cm. É limite computacional V0, não limite arquitetônico.
- Dimensões estritamente positivas; posições negativas são conhecidas e podem provar
  extrapolação, portanto não são substituídas por zero.
- Resultados normalizados e distâncias são strings decimais exatas. Isso representa
  a conta sobre as entradas, não uma alegação sobre precisão de medição física.

## Contratos completos

Veja `SCHEMA.md` e os JSON Schemas em `schemas/`. `spatial_check/contracts.py` é a fonte
de verdade e contém um validador estrito do subconjunto usado, sem bibliotecas externas.
Os arquivos JSON são comparados com o contrato em teste automatizado.

Os campos geométricos são referências a fatos do intake, não números livres. Cada
fato registra `id`, `field`, `value`, `unit`, `meaning`, `source`, `status`.
`INFERRED`, `UNKNOWN` e `CONFLICTING` bloqueiam o campo. `PROVIDED` exige origem de
medição, confirmação ou dimensão documental já admitida pelo chamador. `DERIVED`
só admite conversão de unidade com linhagem completa, recomputada até um `PROVIDED`.
Nenhuma fórmula arbitrária ou fonte fotográfica é executada.

Todas as fontes do mesmo campo são consideradas, não apenas a referência escolhida.
Valores equivalentes em unidades diferentes são aceitos. Divergências bloqueiam; não
há last-write-wins entre mensagens. Resolver conflito exige nova revisão de intake,
com esclarecimento humano/documental, fora do núcleo; não há merge automático.

`meaning` distingue dimensão útil do espaço, dimensão externa do produto montado,
posição, reserva e requisito. Medidas de embalagem ou altura não substituem width/depth.

## Exemplos incluídos

- `fits`: ambiente 300 × 250 cm; móvel 200 × 60 cm; posição `(0,0)`, rotação 0°.
- `clearance_conflict`: mesmo ambiente; móvel 252 × 60 cm; direita requerida 60 cm,
  distância real 48 cm. Conflito.
- `unverified`: largura do espaço desconhecida. Não verificado.

São fixtures sintéticas fornecidas explicitamente. Em T01 e T02, posição `(0,0)` e
rotação 0° fazem parte do fixture; não são escolhidas pelo motor. T01 sem posição
seria `UNVERIFIED` na V0, conforme a regra de não posicionar automaticamente.

## O que não faz

Não projeta, otimiza, busca posição, repara proposta, gera planta, mede imagem,
converte pixels, certifica circulação, declara ABNT/acessibilidade/segurança, avalia
estrutura/instalações ou substitui profissional.
Para nichos, avalia apenas o footprint 2D informado: **não verifica altura, profundidade
de inserção ao longo do percurso, porta de acesso, montagem ou possibilidade de entrega**.

Ausência de conflito não significa móvel comprável, utilizável ou ambiente validado.
Riscos não declarados não podem ser descobertos por este núcleo.

## Revalidação, integridade e testes

Geometria é pura e sem cache. Cada avaliação copia o snapshot e calcula SHA-256 das
entradas. O digest identifica conteúdo; não autentica fonte. O módulo de confiança
mantém estado volátil na autoridade `LifecycleRegistry` (revisão atual, histórico
e sequência de recibos). Um domínio é a autoridade em memória, não o nome do caso.
`HostIntake()` sem argumento cria um domínio independente a cada chamada. Hosts do
mesmo domínio devem compartilhar o MESMO registry; nele, conteúdo diferente para
`(case_id, revision)` é recusado e nova revisão/revogação invalida todos os recibos
antigos do caso, inclusive os emitidos por outro host ligado àquela autoridade.
Revisões são rótulos opacos, sem ordenação numérica implícita.
Não há banco, singleton de autoridade ou persistência. Reiniciar exige novo intake:
um processo novo pode readmitir uma claim antiga. IDs de domínio/recibo são contadores
locais, podem se repetir entre execuções e não servem como identidade global.
`input_digest` continua identificando request + snapshot, sem metadados da admissão.
O resultado é determinístico para o mesmo recibo vigente; readmissões do mesmo
conteúdo podem ter geometria/digests iguais e metadados de recibo diferentes.

Um resultado já exportado não pode ser apagado retroativamente. Ao mudar qualquer
entrada, o host deve confirmar a revisão e chamar o motor novamente, apresentando
sempre o resultado daquele snapshot. Há uma segunda checagem de vigência antes do
retorno; nenhuma validade eterna é prometida após o retorno.

As suítes preservam T01–T12 e os cenários anteriores, adaptando apenas a preparação
para admissão explícita de fixtures sintéticas. Novos testes usam a API real sem essa
conveniência para atacar a confiança, revisar dados e repetir avaliações dos três estados.

## Safety

Sem escala de fotos, dimensão típica, posição presumida ou clearance padrão. Conflito
de fontes gera incerteza. A camada numérica continua recusando INFERRED/UNKNOWN/
CONFLICTING. Confirmação de origem não torna um campo incompleto utilizável.
O modelo não escolhe o resultado. `execution_mode` distingue UNTRUSTED,
HOST_CONFIRMED_INPUT e DEMO_ONLY; não é um quarto estado geométrico.

## Publicação

Esta distribuição contém o componente público independente: núcleo, contratos,
documentação, fixtures sintéticas e testes.

Copyright (c) 2026 Carlos Rafael. Todo o conteúdo desta distribuição é licenciado
sob a Apache License, Version 2.0; veja o texto integral em [LICENSE](LICENSE).
O software é fornecido sem garantias, conforme os termos da licença.
A licença permite reutilização comercial, observadas suas condições; não certifica
medidas, resultados, hosts ou compras. Fonte pública não é confidencial.

Veja `CAPABILITY_MATRIX.md` para capacidades e limites. Não há adapter de plataforma,
frontend, banco, autenticação, rede, otimização ou inteligência visual neste projeto.
