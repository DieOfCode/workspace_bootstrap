# Workspace Bootstrap for Orca

`orca-agent-bootstrap` подготавливает программный проект к контролируемой работе нескольких AI-агентов в Orca.

OpenSpec хранит канонические proposal, requirements, design, tasks, progress и archive. Координатор маршрутизирует эти задачи любым доступным Orca agent/model, проверяет пересечения файлов и принимает evidence. `.agent-workspace` содержит только runtime-состояние и не дублирует план. Все служебные данные остаются локальными и исключаются из Git.

## Установка

```bash
npx skills add https://github.com/DieOfCode/workspace_bootstrap \
  --skill orca-agent-bootstrap \
  --global
```

Либо установите skill через страницу Skills в Orca.

## Локальная структура проекта

```text
AGENTS.md
MEMORY.md
openspec/
.agents/
.agent-workspace/
├── policy.json
├── openspec-config/
├── reports/
├── memory/
│   ├── active/
│   ├── completed/{raw,records,rollups}/
│   ├── decisions/
│   └── verifications/
└── templates/
```

Bootstrap добавляет эти пути в `.gitignore`. Если какой-либо служебный файл уже отслеживается Git, команда останавливается и сообщает команду миграции, но никогда не выполняет `git rm --cached` самостоятельно.

`--init-openspec` устанавливает стандартные OpenSpec skills `explore`, `propose`, `apply`, `update`, `sync` и `archive` в локальную `.agents/`. Для accepted completion соответствующая задача OpenSpec должна быть отмечена выполненной, а change обязан пройти strict validation.

## Использование

```text
Используй $orca-agent-bootstrap и подготовь текущий репозиторий
для локальной работы координатора и фоновых исполнителей.
```

Ручной запуск из каталога skill:

```bash
python3 scripts/workspace.py bootstrap --project /path/to/project --dry-run --json
python3 scripts/workspace.py bootstrap --project /path/to/project --json
python3 scripts/workspace.py bootstrap --project /path/to/project --init-openspec --json
python3 scripts/workspace.py doctor --project /path/to/project --json
python3 scripts/workspace.py doctor --project /path/to/project --apply --json
```

Основные команды:

```bash
python3 scripts/workspace.py risk --project /path/to/project --task task.json --apply --json
python3 scripts/workspace.py conflicts --project /path/to/project --candidate task.json --json
python3 scripts/workspace.py complete --project /path/to/project --task task.json --outcome accepted --json
python3 scripts/workspace.py compact --project /path/to/project --json
python3 scripts/workspace.py scan-secrets --project /path/to/project --json
python3 scripts/workspace.py validate --project /path/to/project --json
```

CLI использует только Python 3.9+ standard library. Он не устанавливает зависимости, не удаляет raw memory, не запускает verifier без явного решения и не создаёт CI workflow.

Skill находится в [`skills/orca-agent-bootstrap`](skills/orca-agent-bootstrap/).
