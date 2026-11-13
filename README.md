# AgendaIQ

Painel de inteligência de agenda para pequenos negócios de serviços. A demonstração ajuda a explorar procura, faltas e capacidade com um conjunto CSV de dados sintéticos; o backend oferece especialistas de IA para analisar os mesmos registros.

> A base em data/appointments.csv foi criada para este protótipo. Não contém dados de clientes reais e os valores não representam receita observada.

## Demonstração

Abra index.html ou publique a raiz no GitHub Pages. O modo público roda cálculos locais, sem enviar conteúdo para um modelo. A ação “Comparar capacidade” ilustra quantos horários adicionais poderiam ser considerados conforme a taxa de preenchimento do conjunto sintético.

Para chamar o backend local pela página, sirva a pasta em um terminal com py -m http.server 5500, abra http://localhost:5500 e inicie a API em outro terminal.

## Rodar os agentes localmente

~~~powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Preencha OPENAI_API_KEY no .env e execute:

~~~powershell
uvicorn api:app --reload
~~~

Na página, informe http://localhost:8000 e use “Consultar agentes”. A chave fica no backend. As perguntas e o resumo agregado são enviados ao provedor do modelo escolhido; a aplicação não mantém histórico de conversas.

## Agentes

- **Analista de procura:** resume padrões por serviço e dia da semana com base no CSV.
- **Planejador de capacidade:** consulta taxas de preenchimento e calcula cenários ilustrativos.
- **Estrategista de retenção:** identifica segmentos sintéticos que podem merecer investigação, sem enviar mensagens.
- **Coordenador:** encaminha a pergunta ao especialista apropriado por handoff.

O backend usa o [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/quickstart).

## Limites

O CSV tem 24 registros fictícios, insuficientes para previsão estatística confiável. A demonstração não agenda, cancela, cobra nem contata clientes. Recomendações precisam ser revisadas por uma pessoa.
