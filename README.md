# ViceDrops6 — MVP para Metricool Free

## O que este projeto faz

Gera **uma fila organizada para os clipes exportados do OpusClip**, com slots para TikTok e Instagram, sem duplicar `clip_id` já confirmado. O GitHub Actions roda sob demanda, após alterações na fila e diariamente. Gera o relatório e o CSV em **Actions > execução > Artifacts**.

**Não publica automaticamente nas redes.** O plano Metricool Free não oferece a API HTTP para scripts externos; a integração Metricool no ChatGPT não fornece credenciais para GitHub Actions. O Metricool Free permite apenas **20 publicações efetivas por mês**, somando as redes. O mesmo vídeo em Instagram + TikTok consome duas. Mesmo usando ChatGPT para agendar, o limite do plano continua aplicável.

Documentação Metricool:
- https://help.metricool.com/pt/planos-complementos-e-acesso-a-api-explicados-xux1u
- https://help.metricool.com/pt/principais-diferencas-entre-os-planos-gratuito-e-pagos-bl0v9

## Começar (sem API paga)

1. Crie repositório **privado** no GitHub `vicedrops6-free`.
2. Extraia o pacote ZIP, entre na pasta `vicedrops6-free` e envie os arquivos ao repositório. Você pode usar GitHub Desktop ou Git:
   ```bash
   git init
   git add .
   git commit -m "ViceDrops6 Free - fila de conteudo"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/vicedrops6-free.git
   git push -u origin main
   ```
3. No Metricool, abra Planejamento e verifique quantas publicações já saíram **neste mês** e quantas ainda estão agendadas. Edite `state/usage.json` com estes números reais, ex.:
   ```json
   {"2026-11":{"published":7,"already_scheduled":3}}
   ```
   **IMPORTANTE:** esses números são um **exemplo**, não uma leitura da sua conta. Se estiverem ausentes ou nulos, o programa não monta publicações.
4. Exporte os MP4 verticais do OpusClip; você **não precisa colocar vídeos no GitHub**. Preencha `inbox/clips.csv` com o nome exato dos arquivos. `media_url` pode ficar vazio quando o vídeo for enviado no ChatGPT.
5. Use `approved=sim` e `rights_cleared=sim` **somente após a sua revisão e autorização apropriada**, inclusive do streamer e demais titulares relevantes. `credit` identifica a origem; não substitui permissão. `platforms=both` agenda nas duas redes, ou escolha uma.
6. Ajuste `config/settings.json`: `slots.tiktok`, `slots.instagram` e `days_between_clips` (padrão: um clipe nas duas redes a cada 3 dias). O programa começa no dia seguinte por padrão.
7. No GitHub vá em **Actions > ViceDrops6 - preparar fila Free > Run workflow**. Depois abra a execução e baixe o artefato `vicedrops6-fila-para-agendar`.
8. Envie `fila_para_agendar.csv` e os MP4 ao ChatGPT e peça o agendamento via Metricool. Confira a confirmação de cada post no Metricool; publicação programada não é publicação concluída.
9. Depois de agendar, adicione os `clip_id` já confirmados, um por linha, em `state/scheduled_clip_ids.txt`, e atualize `state/usage.json` com a soma dos posts efetivos e futuros. Assim evita repetir a sugestão na próxima execução.

## Arquivos

| Arquivo | Função |
|---|---|
| `inbox/clips.csv` | Clipes da fila; comece com `inbox/exemplo.csv` como referência |
| `config/settings.json` | Horários e intervalo entre clipes |
| `state/usage.json` | Contagem manual mensal do Metricool; obrigatório |
| `state/scheduled_clip_ids.txt` | Clipes cujos agendamentos foram confirmados |
| `src/prepare.py` | Cria plano respeitando permissões e a cota mensal |
| `.github/workflows/prepare.yml` | Testes e execução no GitHub Actions |
| `output/` | CSV e relatório criados localmente ou baixados de Actions |

## Rodar localmente

Requer Python 3.11+; não instala dependências externas.

```bash
python -m unittest discover -s tests -v
python src/prepare.py
```

## Limitações importantes

- Não existe upload automático do OpusClip nessa fase. Exportação direta exige um fluxo adicional e acesso adequado ao plano/serviço.
- A fila do GitHub **não verifica agendamentos já criados no Metricool**; atualize manualmente `state/usage.json` e `state/scheduled_clip_ids.txt`.
- Não use URLs temporárias em `media_url`; quando não tiver URL permanente, deixe esse campo vazio e envie o MP4 aqui no ChatGPT.
- GitHub Actions executa tarefas de preparação, mas não deve ser usado como repositório de vídeos grandes ou arquivos com direitos de terceiros.
- Os horários sugeridos são em `America/Sao_Paulo`. O programa agenda a partir do dia seguinte para evitar conflitos de hora.
- A cota Free limita o quanto poderá ser efetivamente publicado; se quiser escala (p. ex. 5 clipes/dia em duas redes), precisará de um plano que comporte o volume ou arquitetura com APIs próprias oficialmente autorizadas.
- Mesmo com autorização do streamer, respeite direitos de imagens do jogo, músicas, pessoas e políticas das plataformas.

## Próxima fase

Upgrade para **Metricool Advanced ou Custom**, com API habilitada, ou integração oficial separada com as plataformas depois de concluir as aprovações necessárias. Aí podemos adaptar o código para publicar após revisão e monitorar resultados sem passar pelo chat.
