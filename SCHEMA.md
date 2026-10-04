# Contrato V0 completo

Os JSON Schemas correspondentes são `schemas/input.schema.json`,
`schemas/evidence.schema.json`, `schemas/result.schema.json`. Nenhuma propriedade
extra é aceita. O runtime ainda faz checagens semânticas além do schema estrutural.

## Request do modelo/chamador

```json
{
  "schema_version": "0.1",
  "case_id": "case-1",
  "revision": "r1",
  "room": {"identity": "room-1", "width": "rw", "depth": "rd"},
  "item": {
    "identity": "product-1", "width": "iw", "depth": "id",
    "position": {"x": "ix", "y": "iy"}, "rotation": "ir"
  },
  "openings": [],
  "explicit_exclusions": [],
  "required_clearances": []
}
```

`schema_version`, `case_id`, `revision`, `room.identity` e `item.identity` são
obrigatórios. Campos métricos são **IDs de evidência**, nunca números. Podem estar
ausentes/null para expressar pendência; essa pendência impede resultado positivo.
Listas opcionais omitidas equivalem a listas vazias somente se o intake também as
declarou vazias. Isso não supõe que o ambiente real não tenha portas.

Reservas de abertura/exclusão:

```json
{"id":"door-1","width":"door-w","depth":"door-d","position":{"x":"door-x","y":"door-y"}}
```

Clearance:

```json
{"id":"front","side":"right","required":"clearance-fact"}
```

`side`: `left`, `right`, `top`, `bottom`, eixos globais após rotação. IDs das restrições
devem ser globalmente únicos. Cada lista tem no máximo 100 registros.

## Claim de intake: JSON candidato, ainda sem confiança

```json
{
  "schema_version":"0.1", "case_id":"case-1", "revision":"r1",
  "room_identity":"room-1", "item_identity":"product-1",
  "declarations":{"openings":[],"explicit_exclusions":[],"required_clearances":[]},
  "facts":[
    {"id":"rw","field":"room.width","value":"3,00","unit":"m",
     "meaning":"usable_width","status":"PROVIDED",
     "source":{"id":"message-1","kind":"user_measurement","locator":"largura útil confirmada"}}
  ]
}
```

Todos os campos de topo são obrigatórios. `declarations.openings` e
`declarations.explicit_exclusions` são arrays de IDs. Clearances são arrays de
`{"id":"front","side":"right"}`. Inventário precisa corresponder exatamente à
proposta. Máximo 1.000 fatos e 2.000.000 caracteres de JSON canônico no par de entradas.
Na CLI cada arquivo também é limitado a 2.000.000 bytes.

Cada fato exige todos os campos exemplificados. IDs: 1–128 caracteres ASCII
alfanuméricos e `_.:/-`, começando por alfanumérico. `source.locator`: texto não vazio
até 4.096 caracteres. Fatos duplicados por ID são erro; vários IDs no mesmo campo
representam fontes alternativas e serão todos verificados.

| `field` | `meaning` exigido | Unidade |
| --- | --- | --- |
| `room.width`, `room.depth` | `usable_width`, `usable_depth` | mm/cm/m |
| `item.width`, `item.depth` | `assembled_width`, `assembled_depth` | mm/cm/m |
| `item.x`, `item.y` | `position_x`, `position_y` | mm/cm/m |
| `item.rotation` | `rotation` | deg |
| `openings.<id>.width/depth` | `reserved_width/reserved_depth` | mm/cm/m |
| `openings.<id>.x/y` | `position_x/position_y` | mm/cm/m |
| `explicit_exclusions.<id>.width/depth` | `reserved_width/reserved_depth` | mm/cm/m |
| `explicit_exclusions.<id>.x/y` | `position_x/position_y` | mm/cm/m |
| `required_clearances.<id>.required` | `required_clearance` | mm/cm/m |

Status: `PROVIDED`, `DERIVED`, `INFERRED`, `UNKNOWN`, `CONFLICTING`.
`value`: inteiro JSON, string decimal ou null; null sempre impede geometria.
`unit`: string ou null; unidade desconhecida bloqueia. Regras numéricas no README.

Fontes admitidas em `PROVIDED`: `user_measurement`, `user_confirmation`,
`document_dimension`. `photo` e `model` não estabelecem métrica, mesmo se o fato for
rotulado PROVIDED. `engine` só é fonte válida para DERIVED com:

```json
"derivation":{"operation":"unit_conversion","input":"parent-fact-id"}
```

Pai deve ter mesmo campo/significado e ser admissível; resultado deve equivaler
exatamente após conversão. Profundidade máxima de linhagem: 32. DERIVED não serve para
inferir dimensão típica, extrair escala de pixels ou executar fórmulas livres.
Registrar metadado como `user_confirmation` não autentica uma confirmação: isso é
responsabilidade do canal de intake, documentada em SECURITY_TRUST_NOTES.md.

## Resultado

| Campo obrigatório | Conteúdo |
| --- | --- |
| `engine_version` | `0.3.0` |
| `execution_mode` | UNTRUSTED, HOST_CONFIRMED_INPUT ou DEMO_ONLY |
| `status` | Um dos três estados públicos exatos do README |
| `case_id`, `revision`, `item_identity` | Identificadores ou null em entrada inválida |
| `admission` | Metadados autoritativos do recibo ou null quando não admitido/vigente na leitura inicial |
| `input_digest` | SHA-256 de request + intake canônicos; null se não serializáveis/fora do limite |
| `findings` | Violações demonstradas |
| `blockers` | Pendências que impedem conclusão completa |
| `checks` | Cada teste, resultado e evidências usadas |
| `evidence` | Snapshot dos fatos de intake após validação estrutural |
| `normalized` | Campos utilizáveis em cm/deg, valor exato e fontes |
| `limitations` | Limitações fixas do núcleo |

Achado/bloqueio: `{code, field, message, evidence_ids}`. Check:
`{id, kind, outcome, evidence_ids}`, com `kind` containment/intersection/clearance,
`outcome` PASS/CONFLICT/BLOCKED. Clearance calculado adiciona `actual_cm` e
`required_cm`, strings; bloqueado não fabrica esses campos.
Campo normalizado: `{field,value,unit,evidence_ids}`, valor em string e unidade cm/deg.

Mensagens não são interpretadas como instruções. `schema_version`, inventário e
identidade são validados antes de avaliar qualquer geometria. Resultado pertence
exclusivamente a este snapshot; não constitui certificação de um ambiente real.


## Fronteira de admissão (ciclo 2)

O JSON acima é EvidenceClaim, **não** o segundo argumento aceito por evaluate.
`claim_from_data(data)` valida e congela a alegação. Somente código de host pode
chamar `HostIntake.confirm(claim, case_id=..., revision=..., room_identity=...,
item_identity=..., confirmation_ref=...)` após revisão independente. O escopo deve
vir do host, não ser copiado automaticamente da claim. Campos não correspondentes
são recusados. Retorno: TrustedEvidence opaco, sem representação JSON.

`evaluate(request, receipt)` retorna UNVERIFIED/TRUST_REQUIRED para objetos livres,
EvidenceClaim, recibos fabricados, revogados ou antigos. Fontes e flags em JSON nunca
emitem recibos. Se o host emite confirmação sem evento real, a biblioteca não pode
autenticar o evento; veja TRUST_BOUNDARY.md. Nenhuma flag verified foi acrescentada.

Engine version 0.3.0; schema_version 0.1 do payload de request/claim permanece porque
a geometria e a estrutura dos dados não mudaram. API Python de confiança mudou.
Resultado inclui execution_mode e admission; o schema de resultado foi atualizado. IDs de checks
podem conter prefixos gerados pelo motor e têm limite de 512 caracteres.

## Patch F2/F3/F5 — contrato 0.3.0 do resultado

Request e claim conservam schema_version 0.1 e estrutura inalterada. O resultado
exige `admission`, null ou objeto estrito com todos estes campos:

```json
{
  "domain_id": "domain-1",
  "receipt_id": "domain-1/receipt-1",
  "confirmation_ref": "confirmation-event-1",
  "evidence_digest": "<SHA-256 de 64 caracteres hexadecimais>",
  "case_id": "case-1",
  "revision": "r1",
  "room_identity": "room-1",
  "item_identity": "product-1"
}
```

Os identificadores usam o contrato ID existente. Metadados vêm do registro emitido
pelo host, jamais do request/claim. confirmation_ref pode se repetir; receipt_id
distingue recibos dentro do processo vivo. IDs podem repetir após reinício.
input_digest não inclui admission e mantém sua definição anterior. Mesmo conteúdo
readmitido pode gerar resultados geometricamente iguais com admission diferente.
Consumidores que validam o schema de resultado 0.2.0 precisam atualizar para 0.3.0.

`HostIntake(registry=None)` aceita opcionalmente um LifecycleRegistry vivo. Ausência
cria domínio novo; compartilhar o objeto é obrigatório para compartilhar lifecycle.
Não aceita rótulo/dicionário como autoridade. Persistência permanece fora do escopo.

A confirmação recusa strings potencialmente ambíguas no formato convencional de
um grupo de milhares, como "1.200"/"1,200", e não emite recibo. Inteiro "1200",
decimais "1.2"/"1,2", "3.20"/"3,20" e "0.000001" continuam aceitos.
Esta é validação semântica além do schema: claims mantêm o token original para
diagnóstico. A confirmação dos números ambíguos precisa de esclarecimento externo
e nova claim; não existe canonicalização automática que escolha o significado.
