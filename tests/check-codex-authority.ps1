Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$marketplacePath = Join-Path $repoRoot '.agents/plugins/marketplace.json'
$pluginRoot = Join-Path $repoRoot 'codex'
$manifestPath = Join-Path $pluginRoot '.codex-plugin/plugin.json'
$skillPath = Join-Path $pluginRoot 'skills/shikigarasu/SKILL.md'
$metadataPath = Join-Path $pluginRoot 'skills/shikigarasu/agents/openai.yaml'
$validationPath = Join-Path $repoRoot 'VALIDATION.md'

foreach ($path in @($marketplacePath, $manifestPath, $skillPath, $metadataPath, $validationPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing Codex plugin file: $path" }
}

$validation = Get-Content -LiteralPath $validationPath -Raw
foreach ($phrase in @('npm test -- --run', 'check-codex-authority.ps1', 'test_probe_shikigarasu_contract.py', 'Codex must', 'same command explicitly')) {
    if (-not $validation.Contains($phrase)) { throw "Validation contract is missing: $phrase" }
}

$marketplace = Get-Content -LiteralPath $marketplacePath -Raw | ConvertFrom-Json
$plugin = @($marketplace.plugins | Where-Object name -eq 'shikigarasu')
if ($marketplace.name -ne 'shikigarasu-codex' -or $plugin.Count -ne 1 -or $plugin[0].source.path -ne './codex') {
    throw 'Marketplace must expose exactly one shikigarasu plugin from ./codex.'
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.name -ne 'shikigarasu' -or $manifest.skills -ne './skills/') {
    throw 'Codex plugin manifest identity or skill root is invalid.'
}

$metadata = Get-Content -LiteralPath $metadataPath -Raw
if ($metadata -notmatch '(?m)^\s*allow_implicit_invocation:\s*true\s*$' -or $metadata -match '(?m)^\s*allow_implicit_invocation:\s*false\s*$') {
    throw 'Shikigarasu must explicitly allow implicit invocation.'
}

$skill = Get-Content -LiteralPath $skillPath -Raw
$frontmatter = $skill.Split('---', 3)[1]
$positiveTriggers = @(
    'multiple substantive independent workstreams',
    'agents, subagents, parallel work, delegation, or coordination',
    'producer plus independent reviewer separation',
    'continue until done',
    'repeated execution and verification',
    'persistent goal'
)
$negativeTriggers = @('one bounded task', 'purely mechanical check')
$body = $skill.Substring($skill.IndexOf('# Shikigarasu'))
foreach ($phrase in $positiveTriggers + $negativeTriggers) {
    if (-not $frontmatter.Contains($phrase) -or -not $body.Contains($phrase)) {
        throw "Trigger boundary must appear in frontmatter and body: $phrase"
    }
}

$contractPhrases = @(
    'READY', 'IN_PROGRESS', 'REVIEW_1', 'REVIEW_2', 'FIX', 'CLOSED', 'BLOCKED',
    'refill freed capacity', 'two review passes', 'fresh-context independent reviewer',
    'producer and both reviewers must be different agents', 'collective ticket ceiling of two fix rounds',
    'newly introduced findings do not reset it', 'Follow the host''s model-routing policy',
    'available lower-cost models', 'strongest available model', 'Never report success'
)
foreach ($phrase in $contractPhrases) {
    if (-not $skill.Contains($phrase)) { throw "Missing self-contained Codex contract phrase: $phrase" }
}

foreach ($forbidden in @('shikigarasu-common', 'dotcodex', 'personal AGENTS', 'C:\', '/Users/', '/home/')) {
    if ($skill.Contains($forbidden)) { throw "Codex skill has a forbidden dependency: $forbidden" }
}

Write-Output 'PASS: public Codex plugin is canonical, implicit, self-contained, and portable'
