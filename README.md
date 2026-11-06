# Workspace Bootstrap for Orca

`orca-agent-bootstrap` подготавливает программный проект к контролируемой работе нескольких AI-агентов в Orca.

Сильный агент выступает координатором: исследует проект, создаёт OpenSpec-план, маршрутизирует ограниченные задачи подходящим исполнителям, принимает вопросы и проверяет результаты. Координатор и исполнители не обязаны использовать один агентный CLI или одного провайдера: например, координатор Codex может запускать Cursor, Antigravity, Claude, OpenCode и другие доступные в Orca агенты. Исполнители работают в отдельных worktree и возвращают доказательства выполнения.

## Что создаётся в проекте

```text
AGENTS.md
MEMORY.md
docs/
├── agent-workflow.md
└── agent-memory/
    ├── active/
    ├── completed/
    ├── decisions/
    └── .templates/
openspec/                  # через официальный OpenSpec CLI
```

- `AGENTS.md` — правила работы координатора и исполнителей.
- `MEMORY.md` — короткая стабильная память проекта.
- `active/` — оперативное состояние выполняемых задач.
- `completed/` — компактные результаты и доказательства.
- `decisions/` — причины архитектурных решений.
- OpenSpec — требования, дизайн и план изменения.

## Установка

```bash
npx skills add https://github.com/DieOfCode/workspace_bootstrap \
  --skill orca-agent-bootstrap \
  --global
```

Либо установите skill через страницу Skills в Orca.

Для запуска попросите агента:

```text
Используй $orca-agent-bootstrap и подготовь текущий репозиторий
для работы сильного координатора и фоновых исполнителей.
Координатор может использовать любые доступные Orca agent/model пары,
а не только собственный агентный CLI или провайдера.
```

## Ручной bootstrap

Из каталога skill:

```bash
cd skills/orca-agent-bootstrap
```

Сначала просмотрите план изменений:

```bash
python3 scripts/bootstrap_project.py --project /path/to/project --dry-run
```

Затем создайте отсутствующие файлы:

```bash
python3 scripts/bootstrap_project.py --project /path/to/project
```

Для инициализации OpenSpec установленным официальным CLI:

```bash
python3 scripts/bootstrap_project.py \
  --project /path/to/project \
  --init-openspec \
  --openspec-tools agents
```

Скрипт не перезаписывает существующие файлы и не устанавливает внешние зависимости автоматически.

## Структура репозитория

Skill находится в [`skills/orca-agent-bootstrap`](skills/orca-agent-bootstrap/). Подробные правила загрузки контекста, оркестрации и памяти находятся в `SKILL.md` и каталоге `references/`.
