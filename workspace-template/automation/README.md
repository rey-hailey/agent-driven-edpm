# 자동화

이 워크스페이스의 자동화는 세 층으로 나뉩니다. 선택 근거는 프레임워크 `guide/04.자동화레이어선택.md`를 보세요.

| 층 | 도구 | 맡는 일 |
|----|------|---------|
| 판단·작성 | Claude Code 스킬 (`.claude/skills/edpm-*`) | ingest, query, lint, 산출물, 주간보고 |
| 웹 수집·화면 점검 | Aside CLI / MCP (`aside/recipes/`) | API가 없는 웹 화면에서 자료 모으기, 스테이징 스모크 테스트 |
| 정해진 일정 실행 | Aside Routines, macOS launchd·cron, GitHub Actions | 매일·매주 반복 |
| 일정 관리 도구 연동 | `scripts/wbs_sync.py` + `wbs.json` (GitHub CLI `gh`) | M02 WBS ↔ GitHub 이슈·마일스톤·Projects, 스프레드시트·Notion·Jira·Linear 내보내기 (`/edpm-wbs`, 프레임워크 `guide/12.일정관리도구연동.md`) |

## 1. Aside 설치와 연결

```bash
# macOS
curl -fsSL https://releases.aside.com/install.sh | bash
aside account status          # 로그인 계정 확인
aside --update                # 업데이트
```

Claude Code에서 Aside를 MCP로 쓰려면 워크스페이스 `.mcp.json`에 추가합니다.

```json
{
  "mcpServers": {
    "aside": { "command": "aside", "args": ["mcp"] }
  }
}
```

출처: [Aside 개발자 문서](https://docs.aside.com/help/developers). Aside는 신생 서비스라 명령·요금·정책이 바뀔 수 있습니다. 레시피는 자연어 지시문이므로 다른 브라우저 에이전트로 옮겨 쓸 수 있습니다.

## 2. 레시피 실행

```bash
automation/scripts/aside-run.sh automation/aside/recipes/R03_교육정책공지모니터링.md --dry-run   # 지시문만 확인
automation/scripts/aside-run.sh automation/aside/recipes/R03_교육정책공지모니터링.md             # 실행 → 00.inbox
```

또는 Claude Code에서 `/edpm-wiki collect R03`. 처음 쓰는 레시피는 `{...}`를 채운 뒤 한 번 직접 돌려 출력을 확인하고, 맞으면 frontmatter `verified_with_aside: true`로 바꿉니다.

## 3. 정기 실행 방법 3가지

### A. Aside Routines (가장 간단)

Aside 앱의 Routines에 레시피 지시문을 그대로 붙여 넣고 주기를 정합니다. 단, 결과 저장 위치를 워크스페이스 `00.inbox/` 절대 경로로 지정하고, Aside의 파일 접근 권한에서 그 폴더를 허용해야 합니다. [확인 필요: Routines에서 로컬 파일 저장이 되는지 처음 설정 때 확인]

### B. macOS launchd (PC가 켜져 있을 때 로컬 실행)

`~/Library/LaunchAgents/com.edpm.r03.plist` 예시 (평일 08:30):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.edpm.r03</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>-lc</string>
    <string>cd ~/Work/회사-edpm && automation/scripts/aside-run.sh automation/aside/recipes/R03_교육정책공지모니터링.md</string>
  </array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>StandardErrorPath</key><string>/tmp/edpm-r03.err</string>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.edpm.r03.plist
```

### C. 주간보고 예약 (Claude Code 헤드리스)

매주 금요일 17:00에 주간보고 초안을 만듭니다. launchd의 `ProgramArguments`를 아래 명령으로 바꿉니다.

```bash
cd ~/Work/회사-edpm && claude -p "/edpm-brief weekly" \
  --allowedTools "Read,Write,Edit,Glob,Grep,Bash(git log:*),Bash(grep:*)"
```

결과는 `04.ops/주간보고/`에 초안으로 저장됩니다. 공유 전에 사람이 검토합니다.

### GitHub Actions를 쓸 때

워크스페이스를 회사 GitHub에 올려 팀과 공유한다면, 결정적인 작업(위키 링크 검사, 개인정보 정규식 검사)은 Actions로 돌립니다. 브라우저 로그인이 필요한 Aside 레시피는 Actions에서 돌리지 않습니다.

## 4. n8n은 언제 쓰나

회사가 이미 n8n을 운영하고 있고, 다음처럼 **서버가 항상 켜져 있어야 하는 이벤트 연동**이 필요할 때 씁니다.

- 이슈 트래커 웹훅 → 팀 메신저 알림
- 배포 완료 → 알림
- 폼 응답(교사 파일럿 신청) → 시트·CRM 등록

이때도 n8n 워크플로우의 결과물(알림 내용, 신청 목록)은 `00.inbox/`로 내보내 위키에 반영합니다.

## 5. 수집 레시피 목록

[aside/README.md](aside/README.md)
