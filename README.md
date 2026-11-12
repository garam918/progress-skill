# progress

Codex와 Claude Code에서 `progress`를 입력하면 현재 프로젝트의 구현률을 읽기 전용으로 확인하는 Agent Skill입니다. 추적표가 있으면 범위와 가중치로 활용합니다. 추적표 없이도 요구사항과 현재 코드로 추정합니다.

> **구현률 약 60%** · README의 MVP 기준, 3/5 가중치.
>
> 남은 핵심 작업은 저장한 메모 목록 표시입니다.

## 채팅에서 설치

Codex나 Claude Code 채팅에 아래 문장을 붙여넣으세요.

> GitHub의 `garam918/progress-skill`에서 `skills/progress` 스킬을 이 도구의 사용자 범위에 설치해줘. 내가 `progress`만 입력하면 이 스킬로 현재 프로젝트의 구현률을 읽기 전용으로 조회하도록 기존 전역 지침에 한 줄 추가해줘.

새 세션에서 프로젝트를 열고 `progress`를 입력합니다. 명시적 호출은 Codex에서 `$progress`, Claude Code에서 `/progress`입니다.

## CLI로 두 도구에 설치

Node.js 22.20 이상에서 실행합니다. [Vercel Skills CLI](https://github.com/vercel-labs/skills)

```bash
npx skills add garam918/progress-skill --skill progress --global --agent codex claude-code --yes --copy
```

CLI로 설치했다면 일반 텍스트 `progress`를 연결하는 [전역 지침 한 줄](skills/progress/README.md#한-단어-호출-연결)도 추가할 수 있습니다. 계산 기준과 추적 CLI는 [스킬 문서](skills/progress/README.md)에 있습니다.

## 테스트

저장소 루트에서 Python 3.10 이상으로 실행합니다.

```bash
python3 -B -m unittest discover -s skills/progress/tests -v
```
