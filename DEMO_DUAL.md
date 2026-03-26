# 🎭 Simulação Dual: Platão × Pinoquio

## Agentes (8 total)

### 📚 Platão (Filosofia)
| Agente | Função |
|--------|--------|
| **Sócrates** | Questionador, método maiêutico |
| **Aristófanes** | Mito dos andróginos, poético |
| **Agaton** | Elogio a Eros, retórico |

### 🎪 Pinoquio (Fantasia)
| Agente | Função |
|--------|--------|
| **Pinóquio** | Boneco curioso, impulsivo |
| **Gepeto** | Pai amoroso, educador |
| **Grilo Falante** | Consciência moral |
| **Fada Azul** | Mágica, redentora |

### 🌉 Ponte (Ambos)
| Agente | Função |
|--------|--------|
| **Hermeneuta** | Compara textos, faz pontes |

## Temas de Discussão

1. **Transformação**: Ascensão platônica vs. jornada de Pinóquio
2. **Mentira/Verdade**: Caverna platônica vs. nariz de Pinóquio
3. **Mentoria**: Sócrates/Diotima vs. Grilo/Gepeto
4. **Desejo**: Eros metafísico vs. querer ser "menino de verdade"

## Como Rodar

### Com Mock (rápido, sem API):
```bash
python3 dual_book_simulation.py --backend mock --rounds 2
```

### Com DeepSeek (lento, real):
```bash
# Requer DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY="sk-..."
python3 dual_book_simulation.py --backend deepseek --rounds 3
```

## Métricas Coletadas

- **Participação por livro**: Mensagens/tokens em cada universo
- **Distância semântica**: Quão diferentes são os dois livros em 1337
- **Referências cruzadas**: RAW objects linkando conceitos entre obras
- **Adaptação de agentes**: Quem navegou ambos os universos

## Exemplo de RAW OO

```json
{
  "id": "uuid",
  "from_book": "plato",
  "to_book": "pinocchio",
  "concept": "metafísica",
  "content": "Como o Belo em si e a humanidade de Pinóquio..."
}
```
