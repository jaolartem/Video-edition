# Edición de video

Repositorio de trabajo para proyectos de edición de video.

## Entorno

- Node.js v24.19.0
- Skills de Remotion instaladas globalmente (`~/.agents/skills`, enlazadas en `~/.claude/skills`)

## Nota sobre git en esta máquina

Norton intercepta HTTPS, por lo que `git clone`/`fetch` sobre HTTPS falla con
`unable to get local issuer certificate (20)`. Solución por comando:

    git -c http.sslBackend=schannel clone <url>

O de forma permanente:

    git config --global http.sslBackend schannel
