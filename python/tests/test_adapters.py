"""Tests for IDE Adapters."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from leet.adapters import (
    create_adapter,
    list_adapters,
    ClaudeCodeAdapter,
    CodexAdapter,
    KimiAdapter,
    AiderAdapter,
)
from leet.adapters.base import (
    AdapterContext,
    AdapterResponse,
    BaseIDEAdapter,
    MessageRole,
    ToolNotFoundError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Testes Base
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdapterContext:
    def test_create_context(self):
        ctx = AdapterContext(
            file_path="main.py",
            project_dir="/project",
            selection="def foo():",
            line_number=10,
            language="python"
        )
        
        assert ctx.file_path == "main.py"
        assert ctx.project_dir == "/project"
        assert ctx.selection == "def foo():"
        assert ctx.line_number == 10
        assert ctx.language == "python"
    
    def test_context_from_vscode(self):
        data = {
            'fileName': 'test.py',
            'workspaceFolder': '/workspace',
            'selectedText': 'selected',
            'lineNumber': 5,
            'languageId': 'python'
        }
        ctx = AdapterContext.from_vscode(data)
        
        assert ctx.file_path == 'test.py'
        assert ctx.project_dir == '/workspace'
        assert ctx.selection == 'selected'
    
    def test_context_projection(self):
        ctx = AdapterContext(
            file_path="main.py",
            selection="code"
        )
        sem, unc = ctx.to_cogon_projection()
        
        assert len(sem) == 32
        assert len(unc) == 32
        # A8_ESTADO deve estar alto com file_path
        assert sem[8] > 0.5
        # A9_PROCESSO deve estar alto com selection
        assert sem[9] > 0.5


class TestAdapterResponse:
    def test_response_success(self):
        resp = AdapterResponse(
            text="Resposta",
            exit_code=0,
            files_modified=["file.py"]
        )
        
        assert resp.success
        assert resp.text == "Resposta"
        assert "file.py" in resp.files_modified
    
    def test_response_failure(self):
        resp = AdapterResponse(
            text="Erro",
            exit_code=1
        )
        
        assert not resp.success
    
    def test_response_to_dict(self):
        resp = AdapterResponse(
            text="Test",
            role=MessageRole.ASSISTANT,
            exit_code=0
        )
        
        d = resp.to_dict()
        assert d['text'] == "Test"
        assert d['role'] == "assistant"
        assert d['exit_code'] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Testes Factory
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactory:
    def test_list_adapters(self):
        adapters = list_adapters()
        assert 'claude' in adapters
        assert 'codex' in adapters
        assert 'kimi' in adapters
        assert 'aider' in adapters
    
    def test_create_adapter_claude(self):
        with patch.object(ClaudeCodeAdapter, '__init__', return_value=None):
            adapter = create_adapter('claude', project_dir='/tmp')
            assert isinstance(adapter, ClaudeCodeAdapter)
    
    def test_create_adapter_codex(self):
        with patch.object(CodexAdapter, '__init__', return_value=None):
            adapter = create_adapter('codex', project_dir='/tmp')
            assert isinstance(adapter, CodexAdapter)
    
    def test_create_adapter_invalid(self):
        with pytest.raises(ValueError):
            create_adapter('invalid')


# ═══════════════════════════════════════════════════════════════════════════════
# Testes Claude Code
# ═══════════════════════════════════════════════════════════════════════════════

class TestClaudeCodeAdapter:
    @pytest.fixture
    def adapter(self, tmp_path):
        with patch.object(ClaudeCodeAdapter, 'is_available', return_value=True):
            return ClaudeCodeAdapter(project_dir=str(tmp_path))
    
    def test_init(self, tmp_path):
        adapter = ClaudeCodeAdapter(project_dir=str(tmp_path))
        assert adapter.name == "claude-code"
        assert adapter.project_dir == str(tmp_path)
    
    def test_init_invalid_dir(self):
        with pytest.raises(ValueError):
            ClaudeCodeAdapter(project_dir="/nonexistent")
    
    def test_build_command(self, adapter):
        cmd = adapter._build_command("Hello", None, None)
        
        assert cmd[0] == "claude"
        assert "--output" in cmd
        assert "Hello" in cmd
    
    def test_build_command_with_context(self, adapter, tmp_path):
        ctx = AdapterContext(file_path=str(tmp_path / "test.py"))
        cmd = adapter._build_command("Hello", ctx, None)
        
        assert "--file" in cmd
    
    def test_extract_file_changes(self, adapter):
        output = """
Edited main.py
Created test.py
Modified README.md
"""
        files = adapter._extract_file_changes(output)
        
        assert "main.py" in files
        assert "test.py" in files


# ═══════════════════════════════════════════════════════════════════════════════
# Testes Codex
# ═══════════════════════════════════════════════════════════════════════════════

class TestCodexAdapter:
    @pytest.fixture
    def adapter(self, tmp_path):
        with patch.object(CodexAdapter, 'is_available', return_value=True):
            return CodexAdapter(project_dir=str(tmp_path))
    
    def test_init(self, tmp_path):
        adapter = CodexAdapter(project_dir=str(tmp_path))
        assert adapter.name == "codex"
        assert adapter.approval_mode == "suggest"
    
    def test_invalid_approval_mode(self, tmp_path):
        with pytest.raises(ValueError):
            CodexAdapter(project_dir=str(tmp_path), approval_mode="invalid")
    
    def test_build_command(self, adapter):
        cmd = adapter._build_command("Hello", None, None)
        
        assert cmd[0] == "codex"
        assert "--approval-mode" in cmd
        assert "suggest" in cmd
        assert "Hello" in cmd


# ═══════════════════════════════════════════════════════════════════════════════
# Testes Kimi
# ═══════════════════════════════════════════════════════════════════════════════

class TestKimiAdapter:
    @pytest.fixture
    def adapter(self, tmp_path):
        return KimiAdapter(project_dir=str(tmp_path))
    
    def test_init(self, tmp_path):
        adapter = KimiAdapter(project_dir=str(tmp_path))
        assert adapter.name == "kimi"
        assert adapter.model == "kimi-k1.5"
    
    def test_api_key_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MOONSHOT_API_KEY", "test-key")
        adapter = KimiAdapter(project_dir=str(tmp_path))
        assert adapter.api_key == "test-key"


# ═══════════════════════════════════════════════════════════════════════════════
# Testes Aider
# ═══════════════════════════════════════════════════════════════════════════════

class TestAiderAdapter:
    @pytest.fixture
    def adapter(self, tmp_path):
        return AiderAdapter(project_dir=str(tmp_path))
    
    def test_init(self, tmp_path):
        adapter = AiderAdapter(project_dir=str(tmp_path))
        assert adapter.name == "aider"
        assert adapter.auto_commit
    
    def test_init_no_project_dir(self):
        with pytest.raises(ValueError):
            AiderAdapter()
    
    def test_git_repo_detection(self, tmp_path):
        # Cria repo git fake
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        
        adapter = AiderAdapter(project_dir=str(tmp_path))
        assert adapter.is_git_repo


# ═══════════════════════════════════════════════════════════════════════════════
# Testes de Integração
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    async def test_mock_send_message(self, tmp_path):
        """Testa envio de mensagem com mock."""
        adapter = KimiAdapter(project_dir=str(tmp_path))
        
        # Mock do método de projeção
        adapter.projector = Mock()
        adapter.projector.project = AsyncMock(return_value=([0.5]*32, [0.1]*32))
        
        # Mock da disponibilidade
        with patch.object(adapter, 'is_available', return_value=False):
            # Não chama API real
            pass
    
    def test_compute_delta(self, tmp_path):
        """Testa computação de delta entre COGONs."""
        from leet import Cogon
        
        adapter = KimiAdapter(project_dir=str(tmp_path))
        
        c1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
        c2 = Cogon.new(sem=[0.7]*32, unc=[0.1]*32)
        
        delta = adapter.compute_delta(c1, c2)
        
        assert len(delta) == 32
        # Delta deve ser ~0.2
        assert abs(delta[0] - 0.2) < 0.01
