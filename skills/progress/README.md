# progress

Codex 또는 Claude Code에서 프로젝트를 열고 `progress`만 입력하세요.

> **구현률 약 60%** · README의 MVP 기준, 3/5 가중치.
>
> 남은 핵심 작업은 저장한 메모 목록 표시입니다.

추적표가 있으면 작업 범위와 가중치를 사용하고, 완료 여부는 현재 코드를 확인해 판단합니다. 추적표가 없는 프로젝트에서는 README, 요구사항, 테스트와 코드로 범위를 추정합니다. 집계할 범위를 찾기 어려우면 이유를 한 줄로 알려줍니다. 조회 중에는 프로젝트 파일을 쓰거나 테스트를 실행하지 않습니다.

## 한 번만 설치하기

### Codex 또는 Claude Code 채팅에서 설치

아래 문장을 채팅에 붙여넣으세요.

> GitHub의 `garam918/progress-skill`에서 `skills/progress` 스킬을 이 도구의 사용자 범위에 설치해줘. 내가 `progress`만 입력하면 이 스킬로 현재 프로젝트의 구현률을 읽기 전용으로 조회하도록 기존 전역 지침에 한 줄 추가해줘.

셸에서 두 도구에 한 번에 설치할 수도 있습니다. `npx skills`에는 Node.js 22.20 이상이 필요합니다. 비공개 저장소라면 설치하는 환경에서 해당 저장소를 읽을 수 있어야 합니다. [Vercel Skills CLI](https://github.com/vercel-labs/skills)

```bash
npx skills add garam918/progress-skill --skill progress --global --agent codex claude-code --yes --copy
```

### ZIP으로 설치

아래는 macOS, Linux, WSL에서 두 도구에 사용자 범위로 설치하는 예입니다. 압축을 푼 폴더에서 실행하세요.

```bash
unzip progress.zip
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
cp -R progress "$HOME/.agents/skills/"
cp -R progress "$HOME/.claude/skills/"
```

### 한 단어 호출 연결

`progress` 한 단어를 명확히 연결하려면 아래 한 줄을 Codex의 `~/.codex/AGENTS.md`와 Claude Code의 `~/.claude/CLAUDE.md`에 각각 추가하세요. 기존 내용은 유지합니다. [Codex 사용자 지침](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Claude Code 사용자 지침](https://code.claude.com/docs/en/memory)

```markdown
If my entire message is `progress`, read the installed `progress` skill's SKILL.md and use its read-only quick check for the current project.
```

새 세션부터 모든 프로젝트에서 `progress`를 입력할 수 있습니다. 일반 텍스트는 모델이 스킬로 연결합니다. 명시적으로 호출할 때는 Codex에서 `$progress`, Claude Code에서 `/progress`를 사용하세요. [Codex 스킬 문서](https://learn.chatgpt.com/docs/build-skills), [Claude Code 스킬 문서](https://code.claude.com/docs/en/skills)

## 필요할 때만 사용하는 기능

- [읽기 전용 구현률 계산](references/quick-check.md)은 Python 3.10 이상에서 실행됩니다. Python을 쓸 수 없는 환경에서도 스킬은 같은 계산식을 사용합니다.
- [추적 CLI](references/tracker-format.md)는 기존 `.progress/tasks.json` 형식을 그대로 읽으며, 요청 시에만 상태 변경이나 보고서 저장에 사용합니다. 상태 쓰기는 macOS, Linux, WSL의 로컬 파일시스템을 지원합니다.
- 압축을 푼 폴더에서 `python3 -B -m unittest discover -s progress/tests -v`로 테스트합니다.
