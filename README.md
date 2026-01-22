[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/fNIvjsmp)

# SandboxIA

## Overview

- 서비스 소개
- 주요 기능
- 전체 아키텍처 (Client / Server)
- 기술 스택 요약

## Repository Structure

```
.
├── client/                # Next.js 프론트엔드
│   ├── ...
│   └── README.md
├── server/                # FastAPI 백엔드
│   ├──  ...
│   └── README.md
├── doc/                   # 프로젝트 문서
├── README.md
└── CLAUDE.md              # Claude Code 지침 문서
```

## Getting Started

자세한 설정은 각 디렉토리의 README 문서 참고:

- [client/README.md](./client/README.md)
- [server/README.md](./server/README.md)

## Contributing

### 브랜치 전략

- `main`: 프로덕션
- `dev`: 개발
- `baseline`: 초기 프로젝트 세팅
- `feature/agent-{에이전트명}`: 에이전트 개발
- `feature/tool-{툴명}`: 툴 개발
- `feature/func-{기능명}`: 기능 개발
- `feature/uiux`: client 화면 개발

### PR 워크플로우

**PR 방향:**

| From | To | 설명 |
|------|----|------|
| `feature/*`, `fix/*` 등 | `dev` | 기능 개발 완료 시 |
| `dev` | `main` | 배포 시 |

**올바른 PR 생성 방법:**

```bash
# 1. 내 작업 브랜치에서 작업 완료 후 커밋
git checkout feature/my-feature
git add .
git commit -m "feat: 새 기능 추가"

# 2. 내 브랜치를 원격에 push
git push origin feature/my-feature

# 3. GitHub 웹사이트에서 PR 생성
#    - base 브랜치를 dev (또는 main)로 설정
#    - compare 브랜치를 내 작업 브랜치로 설정
```

> **주의:** dev나 main으로 checkout해서 pull/merge 하지 마세요!
> PR은 GitHub 웹에서 생성하고, 리뷰 후 "Merge" 버튼으로 머지합니다.

### CodeRabbit (AI 코드 리뷰)

이 프로젝트는 [CodeRabbit](https://coderabbit.ai)을 사용하여 자동 코드 리뷰를 수행합니다.

**동작 방식:**
1. `dev` 또는 `main` 브랜치로 PR 생성
2. CodeRabbit이 자동으로 코드 분석 및 리뷰 코멘트 작성
3. 리뷰 내용 확인 후 필요시 코드 수정
4. 리뷰 완료 후 "Merge pull request" 버튼 클릭

**설정 파일:** `.coderabbit.yaml`

## 👥 Team

AI Camp 4th - Team SandboxIA
