param(
    [string]$SkillPath,
    [string]$DispatchPath,
    [string]$ReadmePath,
    [string]$AgentReadmePath,
    [string]$KishiPath,
    [string]$ShuenPath,
    [string]$HakusoPath,
    [string]$SoenPath,
    [string]$AgentDirPath,
    [string[]]$MemoryAdapterPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $SkillPath) { $SkillPath = Join-Path $HOME '.claude/skills/shikigarasu-common/SKILL.md' }
if (-not $DispatchPath) { $DispatchPath = Join-Path $repoRoot 'rules/common/shikigarasu-dispatch.md' }
if (-not $ReadmePath) { $ReadmePath = Join-Path $repoRoot 'README.md' }
if (-not $AgentReadmePath) { $AgentReadmePath = Join-Path $repoRoot 'docs/agents.md' }
if (-not $AgentDirPath) { $AgentDirPath = Join-Path $repoRoot 'agents' }
if (-not $KishiPath) { $KishiPath = Join-Path $AgentDirPath 'kishi.md' }
if (-not $ShuenPath) { $ShuenPath = Join-Path $AgentDirPath 'shuen.md' }
if (-not $HakusoPath) { $HakusoPath = Join-Path $AgentDirPath 'hakuso.md' }
if (-not $SoenPath) { $SoenPath = Join-Path $AgentDirPath 'soen.md' }
if (-not $MemoryAdapterPath) { $MemoryAdapterPath = @((Get-ChildItem (Join-Path $repoRoot 'commands') -Filter *.md).FullName + (Get-ChildItem (Join-Path $repoRoot 'skills') -Filter *.md).FullName) }

function Read-AgentFrontmatter([string]$Path) {
    $content = Get-Content -Raw $Path
    if ($content -notmatch '(?s)\A---\r?\n(.*?)\r?\n---') { throw "Missing first YAML frontmatter block: $Path" }
    $block = $Matches[1]
    $modelMatches = [regex]::Matches($block, '(?m)^model:\s*(\S+)\s*$')
    $toolsMatches = [regex]::Matches($block, '(?m)^tools:\s*(.+?)\s*$')
    if ($modelMatches.Count -ne 1 -or $toolsMatches.Count -ne 1) { throw "Frontmatter must contain exactly one model and one tools key: $Path" }
    $model = $modelMatches[0].Groups[1].Value
    $toolsText = $toolsMatches[0].Groups[1].Value
    if (-not $model -or -not $toolsText) { throw "Missing model/tools in frontmatter: $Path" }
    [pscustomobject]@{ Model = $model; Tools = @($toolsText -split ',' | ForEach-Object { $_.Trim() }) }
}

$skill = Get-Content -Raw $SkillPath
$cases = [ordered]@{
    'queue: delegate within available capacity, no fixed cap' = @('Delegate every substantive ready ticket', 'refill freed capacity', 'no fixed cap to total ticket count', 'without blocking authorized work')
    'independent review: producer and reviewers differ' = @('fresh-context independent reviewer', 'producer and both reviewers must be different workers', 'They never close a ticket')
    'convergence: collective ceiling on fix rounds' = @('two review passes', 'collective ticket ceiling', 'newly introduced findings do not reset')
    'evidence: closure requires both passes on final result' = @('Close only after both passes', 'Never report success for a ticket that has not passed both closure gates')
}

$failed = 0
foreach ($case in $cases.GetEnumerator()) {
    $missing = @($case.Value | Where-Object { -not $skill.Contains($_) })
    if ($missing.Count) {
        Write-Output "FAIL: $($case.Key)"
        $missing | ForEach-Object { Write-Output "  missing: $_" }
        $failed++
    } else {
        Write-Output "PASS: $($case.Key)"
    }
}

Write-Output "$($cases.Count - $failed)/$($cases.Count) contract cases passed"
if ($DispatchPath) {
    $dispatch = Get-Content -Raw $DispatchPath
    $dispatchCases = [ordered]@{
        'dispatch is self-contained and capacity-aware' = @('currently available subagent slots', 'Refill freed slots', 'no fixed cap', 'without blocking authorized work', 'do not stack Kishi flows')
        'dispatch preserves persistence and external boundaries' = @('/goal', 'irreversible external action', 'when available', 'report the unsupported persistence requirement')
        'dispatch uses one capable coordinator' = @('main session applies the Kishi coordinator protocol directly', 'exactly one `claude --agent kishi -p', 'Never start one CLI process per ticket')
    }
    foreach ($case in $dispatchCases.GetEnumerator()) {
        $missing = @($case.Value | Where-Object { -not $dispatch.Contains($_) })
        if ($dispatch.Contains('agents.md')) { $missing += 'must not depend on agents.md' }
        if ($dispatch.Contains('subagent_type="kishi"')) { $missing += 'must not assume nested Kishi dispatch capability' }
        if ($missing.Count) {
            Write-Output "FAIL: $($case.Key)"
            $missing | ForEach-Object { Write-Output "  missing: $_" }
            $failed++
        } else {
            Write-Output "PASS: $($case.Key)"
        }
    }
}

if ($ReadmePath) {
    $readme = Get-Content -Raw $ReadmePath
    $readmeCases = [ordered]@{
        'orchestrated example shows two distinct final reviewers' = @('Hakuso reviewer 1', 'Hakuso reviewer 2', 'after the final change')
        'Soen is Agent-only' = @('Soen is Agent-only', 'no `/shikigarasu:soen` slash command')
        'documented agent models match frontmatter' = @('| `kishi` | 鬼子 | Coordinator — dispatches workers, synthesizes | sonnet |', '| `seiran` | 青嵐 | Strategy — bounded tradeoff analysis | opus |', '| `shuen` | 朱焔 | Scout — blind spots, assumption stress-test | sonnet |', '| `genen` | 玄淵 | Execution — build, refactor, fix | sonnet |', '| `hakuso` | 白霜 | Audit — pass/block verdict | opus |', '| `soen` | 蒼炎 | Scientist — hypothesis-driven experiments | sonnet |')
        'plugin lifecycle distinguishes namespaced and copied entrypoints' = @('namespaced agents, commands, and rules', 'unnamespaced personal agent entrypoints', 'Disabling the plugin removes its namespaced components', 'copied personal agents remain')
    }
    foreach ($case in $readmeCases.GetEnumerator()) {
        $missing = @($case.Value | Where-Object { -not $readme.Contains($_) })
        if ($case.Key -eq 'Soen is Agent-only' -and ($readme -match '(?m)^\s*/shikigarasu:soen\b' -or $readme -match 'Provides[^\.\r\n]*/shikigarasu:soen[^\.\r\n]*as slash commands')) { $missing += 'must not advertise /shikigarasu:soen' }
        if ($missing.Count) {
            Write-Output "FAIL: $($case.Key)"
            $missing | ForEach-Object { Write-Output "  missing: $_" }
            $failed++
        } else {
            Write-Output "PASS: $($case.Key)"
        }
    }
    if ($readme.Contains('plugin provides slash commands only') -or $readme.Contains('does not remove agents or rules')) { Write-Output 'FAIL: stale slash-commands-only lifecycle claim'; $failed++ } else { Write-Output 'PASS: no stale slash-commands-only lifecycle claim' }
}

if ($AgentReadmePath) {
    $agentReadme = Get-Content -Raw $AgentReadmePath
    $required = @('| `kishi.md` | 鬼子 Kishi | Coordinator — dispatches workers, synthesizes | sonnet |', '| `seiran.md` | 青嵐 Seiran | Strategy — bounded tradeoff analysis | opus |', '| `shuen.md` | 朱焔 Shuen | Scout — blind spots, assumption stress-test | sonnet |', '| `genen.md` | 玄淵 Genen | Execution — build, refactor, fix | sonnet |', '| `hakuso.md` | 白霜 Hakuso | Audit — pass/block verdict | opus |', '| `soen.md` | 蒼炎 Soen | Scientist — hypothesis-driven experiments | sonnet |', 'four slash commands', 'Soen is Agent-only', 'no `/shikigarasu:soen` slash command')
    $missing = @($required | Where-Object { -not $agentReadme.Contains($_) })
    if ($agentReadme.Contains('Kishi, Shuen, Soen')) { $missing += 'must not claim Kishi vault/memory writes' }
    if ($missing.Count) {
        Write-Output 'FAIL: agents README matches portable adapter surface'
        $missing | ForEach-Object { Write-Output "  missing: $_" }
        $failed++
    } else {
        Write-Output 'PASS: agents README matches portable adapter surface'
    }
}

if ($AgentDirPath) {
    $expected = [ordered]@{
        'kishi.md' = @{ Model = 'sonnet'; Tools = @('Agent','SendMessage','TaskCreate','TaskUpdate','TaskGet','TaskList','TaskOutput','Read','Glob') }
        'seiran.md' = @{ Model = 'opus'; Tools = @('Read','Grep','Glob','WebSearch','WebFetch') }
        'shuen.md' = @{ Model = 'sonnet'; Tools = @('WebFetch','WebSearch','Read','Grep','Glob','Write') }
        'genen.md' = @{ Model = 'sonnet'; Tools = @('Read','Grep','Glob','Edit','Write','Bash') }
        'hakuso.md' = @{ Model = 'opus'; Tools = @('Read','Grep','Glob','Bash','Write') }
        'soen.md' = @{ Model = 'sonnet'; Tools = @('Read','Grep','Glob','Bash','Write','WebFetch','WebSearch') }
    }
    foreach ($entry in $expected.GetEnumerator()) {
        $actual = Read-AgentFrontmatter (Join-Path $AgentDirPath $entry.Key)
        $expectedTools = @($entry.Value.Tools | Sort-Object)
        $actualTools = @($actual.Tools | Sort-Object)
        $modelMatches = $actual.Model -eq $entry.Value.Model
        $toolsMatch = $expectedTools.Count -eq $actualTools.Count -and -not (Compare-Object $expectedTools $actualTools)
        if (-not $modelMatches -or -not $toolsMatch) { Write-Output "FAIL: agent frontmatter parity: $($entry.Key)"; Write-Output "  expected model/tools: $($entry.Value.Model) / $($expectedTools -join ', ')"; Write-Output "  actual model/tools: $($actual.Model) / $($actualTools -join ', ')"; $failed++ } else { Write-Output "PASS: agent frontmatter parity: $($entry.Key)" }
    }
    if (Test-Path (Join-Path $AgentDirPath 'README.md')) { Write-Output 'FAIL: agents directory contains auto-discovered README.md'; $failed++ } else { Write-Output 'PASS: agents directory contains agent definitions only' }
}

if ($KishiPath) {
    $kishi = Get-Content -Raw $KishiPath
    $required = @('Coordinate; do not execute', 'If `Agent` is unavailable', 'Mis-invoked without Agent dispatch capability.', 'Then stop.', 'two review passes', 'producer and both reviewers must be different agents', 'Refill freed slots', 'collective ticket ceiling')
    $missing = @($required | Where-Object { -not $kishi.Contains($_) })
    if ($kishi -match 'description:[^\r\n]*Agent\(subagent_type=kishi\)') { $missing += 'Kishi description must not advertise nested invocation' }
    if ($missing.Count) {
        Write-Output 'FAIL: actual Kishi has coordinator capability and closure gates'
        $missing | ForEach-Object { Write-Output "  missing: $_" }
        $failed++
    } else {
        Write-Output 'PASS: actual Kishi has coordinator capability and closure gates'
    }
}

if ($ShuenPath) {
    $shuen = Get-Content -Raw $ShuenPath
    $required = @('tools: WebFetch, WebSearch, Read, Grep, Glob, Write', 'Kishi-provided report path', 'OS temp report path', 'map `shikigarasu:` to `ski_dir`', 'both `agents_vault` and `shikigarasu`', 'skip optional memory', 'Do not write to vault')
    $missing = @($required | Where-Object { -not $shuen.Contains($_) })
    if ($shuen.Contains('Kishi handles synthesis-level vault writes')) { $missing += 'must not claim Kishi writes vault' }
    if ($missing.Count) { Write-Output 'FAIL: Shuen report and memory capability'; $missing | ForEach-Object { Write-Output "  missing: $_" }; $failed++ } else { Write-Output 'PASS: Shuen report and memory capability' }
}

if ($HakusoPath) {
    $hakuso = Get-Content -Raw $HakusoPath
    $required = @('model: opus', 'native fresh-context reviewer', 'high-risk', 'explicitly allocated and accounted for by Kishi', 'Do not run snapshot-update, coverage, or other write-capable test modes', 'verify the worktree is unchanged')
    $missing = @($required | Where-Object { -not $hakuso.Contains($_) })
    if ($hakuso -match '(?m)^\s*- \*\*(Primary|Fallback)\*\*:.*(agy|codex)') { $missing += 'must not mandate detached agy/codex readers' }
    if ($missing.Count) { Write-Output 'FAIL: Hakuso review capability'; $missing | ForEach-Object { Write-Output "  missing: $_" }; $failed++ } else { Write-Output 'PASS: Hakuso review capability' }
}

if ($SoenPath) {
    $soen = Get-Content -Raw $SoenPath
    $required = @('If either `vault` or `research` is absent or unresolved', 'fall back to OS temp', 'Never construct a partial vault path')
    $missing = @($required | Where-Object { -not $soen.Contains($_) })
    if ($missing.Count) { Write-Output 'FAIL: Soen complete vault-path fallback'; $missing | ForEach-Object { Write-Output "  missing: $_" }; $failed++ } else { Write-Output 'PASS: Soen complete vault-path fallback' }
}

foreach ($path in $MemoryAdapterPath) {
    $adapter = Get-Content -Raw $path
    if (-not $adapter.Contains('skip optional memory reads and writeback')) {
        Write-Output "FAIL: missing-config memory fallback: $path"
        $failed++
    } else {
        Write-Output "PASS: missing-config memory fallback: $path"
    }
}

$shuenAdapters = @((Join-Path $repoRoot 'commands/shuen.md'), (Join-Path $repoRoot 'skills/shuen.md'))
foreach ($path in $shuenAdapters) {
    $adapter = Get-Content -Raw $path
    $required = @('Both `agents_vault` and `shikigarasu`', 'skip optional memory reads and writeback')
    $missing = @($required | Where-Object { -not $adapter.Contains($_) })
    if ($adapter.Contains('if `shikigarasu:` is absent, use `shikigarasu/`')) { $missing += 'must not default missing shikigarasu key' }
    if ($missing.Count) { Write-Output "FAIL: strict Shuen config parity: $path"; $missing | ForEach-Object { Write-Output "  missing: $_" }; $failed++ } else { Write-Output "PASS: strict Shuen config parity: $path" }
}

# Shared shikigarasu-common contract: no duplicate identity, synced mirrors, adapter reference, tightened persistence
$dupSkillPath = Join-Path $repoRoot 'agent-skills/shikigarasu'
if (Test-Path $dupSkillPath) { Write-Output 'FAIL: plugin repo has no duplicate agent-skills/shikigarasu'; $failed++ } else { Write-Output 'PASS: plugin repo has no duplicate agent-skills/shikigarasu' }

$claudeSharedSkill = Join-Path $HOME '.claude/skills/shikigarasu-common/SKILL.md'
if ((Test-Path $claudeSharedSkill) -and (Get-Content -Raw $claudeSharedSkill).Contains('name: shikigarasu-common')) { Write-Output 'PASS: Claude runtime skills carries shikigarasu-common' } else { Write-Output 'FAIL: Claude runtime skills carries shikigarasu-common'; $failed++ }

$dotclaudeSharedSkill = 'C:/Code/dotclaude/agent-skills/shikigarasu-common/SKILL.md'
$dotclaudeOldSkill = 'C:/Code/dotclaude/agent-skills/shikigarasu'
if ((Test-Path $dotclaudeSharedSkill) -and -not (Test-Path $dotclaudeOldSkill)) { Write-Output 'PASS: dotclaude mirrors shikigarasu-common, old identity gone' } else { Write-Output 'FAIL: dotclaude mirrors shikigarasu-common, old identity gone'; $failed++ }

$claudeOldSkill = Join-Path $HOME '.claude/skills/shikigarasu'
$agentsOldSkill = Join-Path $HOME '.agents/skills/shikigarasu'
if (-not (Test-Path $claudeOldSkill) -and -not (Test-Path $agentsOldSkill)) { Write-Output 'PASS: no shared/native collision on the shikigarasu identity' } else { Write-Output 'FAIL: no shared/native collision on the shikigarasu identity'; $failed++ }

if ($ReadmePath -and $KishiPath -and (Test-Path $ReadmePath) -and (Test-Path $KishiPath)) {
    $readmeText = Get-Content -Raw $ReadmePath
    $kishiText = Get-Content -Raw $KishiPath

    if ($kishiText.Contains('shikigarasu-common') -and $readmeText.Contains('shikigarasu-common')) { Write-Output 'PASS: Claude adapter references the shared shikigarasu-common contract' } else { Write-Output 'FAIL: Claude adapter references the shared shikigarasu-common contract'; $failed++ }

    $goalRegex = '/goal.{0,15}(or an? equivalent|or equiv)'
    $persistencePhrase = 'explicitly requests persistent continuation'
    if (($readmeText -notmatch $goalRegex) -and ($kishiText -notmatch $goalRegex) -and $readmeText.Contains($persistencePhrase) -and $kishiText.Contains($persistencePhrase)) { Write-Output 'PASS: README and kishi.md persistence boundary tightened' } else { Write-Output 'FAIL: README and kishi.md persistence boundary tightened'; $failed++ }

    if ($kishiText.Contains('producer and both reviewers must be different agents')) { Write-Output 'PASS: producer excluded from serving as either reviewer' } else { Write-Output 'FAIL: producer excluded from serving as either reviewer'; $failed++ }

    $anchorsHeld = $kishiText.Contains('Require two review passes for every completed ticket, including when the first pass reports no findings.') -and $kishiText.Contains('A failed ticket may reopen only as a strictly narrower ticket.')
    if ($anchorsHeld) { Write-Output 'PASS: two review passes and reopen-narrower/cap sentences unchanged' } else { Write-Output 'FAIL: two review passes and reopen-narrower/cap sentences unchanged'; $failed++ }
}

if ($DispatchPath -and (Test-Path $DispatchPath)) {
    $dispatchText = Get-Content -Raw $DispatchPath
    $goalRegex = '/goal.{0,15}(or an? equivalent|or equiv)'
    if (($dispatchText -notmatch $goalRegex) -and $dispatchText.Contains('explicitly requests persistent continuation')) { Write-Output 'PASS: dispatch rule persistence boundary tightened' } else { Write-Output 'FAIL: dispatch rule persistence boundary tightened'; $failed++ }
}

if ($failed) { exit 1 }
exit 0
