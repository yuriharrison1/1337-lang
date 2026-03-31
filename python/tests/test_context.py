"""
Testes para o módulo de context-aware projection.
"""

import pytest
from leet.context import (
    ContextProfile, ContextManager,
    get_context_manager, set_context_profile, adjust_with_context,
)
from leet.types import Cogon, FIXED_DIMS


class TestContextProfile:
    """Testes para ContextProfile."""
    
    def test_creation(self):
        """Criação básica de perfil."""
        profile = ContextProfile(
            name="test",
            description="Test profile",
            axis_weights=[0.5] * FIXED_DIMS,
            temperature=1.0,
        )
        
        assert profile.name == "test"
        assert profile.description == "Test profile"
        assert len(profile.axis_weights) == FIXED_DIMS
    
    def test_to_cogon(self):
        """Conversão para COGON."""
        profile = ContextProfile(
            name="technical",
            description="Technical context",
            axis_weights=[0.9 if i in [7, 8, 9] else 0.5 for i in range(FIXED_DIMS)],
            dominant_axes=[7, 8, 9],
        )
        
        cogon = profile.to_cogon()
        assert len(cogon.sem) == FIXED_DIMS
        assert len(cogon.unc) == FIXED_DIMS
        # Eixos dominantes devem ter menor incerteza
        assert cogon.unc[7] < cogon.unc[10]
    
    def test_serialization(self):
        """Serialização/deserialização."""
        profile = ContextProfile(
            name="test",
            description="Test",
            axis_weights=[0.6] * FIXED_DIMS,
            dominant_axes=[1, 2, 3],
        )
        
        data = profile.to_dict()
        restored = ContextProfile.from_dict(data)
        
        assert restored.name == profile.name
        assert restored.axis_weights == profile.axis_weights
        assert restored.dominant_axes == profile.dominant_axes


class TestContextManager:
    """Testes para ContextManager."""
    
    @pytest.fixture
    def manager(self):
        """Fixture para ContextManager limpo."""
        return ContextManager(window_size=5)
    
    def test_builtin_profiles(self, manager):
        """Perfis built-in disponíveis."""
        assert "technical" in manager.BUILTIN_PROFILES
        assert "emergency" in manager.BUILTIN_PROFILES
        assert "philosophical" in manager.BUILTIN_PROFILES
    
    def test_set_profile(self, manager):
        """Definir perfil ativo."""
        profile = manager.set_profile("technical")
        
        assert manager.current_profile is not None
        assert manager.current_profile.name == "technical"
        assert profile.usage_count == 1
    
    def test_invalid_profile(self, manager):
        """Perfil inválido deve falhar."""
        with pytest.raises(ValueError):
            manager.set_profile("nonexistent")
    
    def test_add_to_history(self, manager):
        """Adicionar COGON ao histórico."""
        cogon = Cogon.new(sem=[0.5] * FIXED_DIMS, unc=[0.1] * FIXED_DIMS)
        
        manager.add_to_history(cogon)
        assert len(manager.history) == 1
        
        manager.add_to_history(cogon)
        assert len(manager.history) == 2
    
    def test_history_window_size(self, manager):
        """Histórico respeita tamanho da janela."""
        manager = ContextManager(window_size=3)
        
        for i in range(5):
            cogon = Cogon.new(sem=[i/10] * FIXED_DIMS, unc=[0.1] * FIXED_DIMS)
            manager.add_to_history(cogon)
        
        assert len(manager.history) == 3
    
    def test_get_context_cogon_no_history(self, manager):
        """Contexto sem histórico retorna None."""
        cogon = manager.get_context_cogon()
        assert cogon is None
    
    def test_get_context_cogon_with_profile(self, manager):
        """Contexto com perfil definido."""
        manager.set_profile("technical")
        cogon = manager.get_context_cogon()
        
        assert cogon is not None
        assert len(cogon.sem) == FIXED_DIMS
    
    def test_get_context_cogon_with_history(self, manager):
        """Contexto com histórico."""
        for i in range(3):
            cogon = Cogon.new(sem=[0.5 + i*0.1] * FIXED_DIMS, unc=[0.1] * FIXED_DIMS)
            manager.add_to_history(cogon)
        
        context = manager.get_context_cogon()
        assert context is not None
    
    def test_adjust_projection(self, manager):
        """Ajustar projeção com contexto."""
        # Define um perfil que enfatiza urgência
        manager.set_profile("emergency")
        
        sem = [0.5] * FIXED_DIMS
        unc = [0.2] * FIXED_DIMS
        
        adjusted_sem, adjusted_unc = manager.adjust_projection(sem, unc, context_alpha=0.3)
        
        assert len(adjusted_sem) == FIXED_DIMS
        assert len(adjusted_unc) == FIXED_DIMS
        # Valores devem ser diferentes após ajuste
        assert adjusted_sem != sem or adjusted_unc != unc
    
    def test_adjust_projection_no_context(self, manager):
        """Ajuste sem contexto retorna original."""
        sem = [0.5] * FIXED_DIMS
        unc = [0.2] * FIXED_DIMS
        
        adjusted_sem, adjusted_unc = manager.adjust_projection(sem, unc)
        
        assert adjusted_sem == sem
        assert adjusted_unc == unc
    
    def test_detect_context_drift(self, manager):
        """Detecção de mudança de contexto."""
        # Histórico vazio - sem drift
        assert manager.detect_context_drift() is None
        
        # Adiciona COGONs similares
        for _ in range(3):
            cogon = Cogon.new(sem=[0.5] * FIXED_DIMS, unc=[0.1] * FIXED_DIMS)
            manager.add_to_history(cogon)
        
        # Ainda sem drift (similares)
        assert manager.detect_context_drift(threshold=0.5) is None
    
    def test_create_custom_profile(self, manager):
        """Criar perfil customizado."""
        
        def mock_project(text: str):
            # Mock simples (função regular, não async)
            sem = [0.5] * FIXED_DIMS
            if "urgente" in text:
                sem[22] = 0.9  # urgência
            return sem, [0.1] * FIXED_DIMS
        
        profile = manager.create_custom_profile(
            name="custom",
            description="Custom profile",
            sample_texts=["Situação urgente", "Problema crítico"],
            project_fn=mock_project,
        )
        
        assert profile.name == "custom"
        assert "custom" in manager.custom_profiles
        assert len(profile.dominant_axes) == 5
    
    def test_import_export_profile(self, manager, tmp_path):
        """Importar/exportar perfil."""
        manager.set_profile("technical")
        
        export_path = tmp_path / "profile.json"
        manager.export_profile("technical", str(export_path))
        
        assert export_path.exists()
        
        imported = manager.import_profile(str(export_path))
        assert imported.name == "technical"
    
    def test_get_stats(self, manager):
        """Estatísticas do contexto."""
        stats = manager.get_stats()
        
        assert "history_size" in stats
        assert "window_size" in stats
        assert "available_profiles" in stats


class TestGlobalContext:
    """Testes para funções globais de contexto."""
    
    def test_get_context_manager_singleton(self):
        """get_context_manager retorna singleton."""
        m1 = get_context_manager()
        m2 = get_context_manager()
        assert m1 is m2
    
    def test_set_context_profile_global(self):
        """set_context_profile define globalmente."""
        profile = set_context_profile("philosophical")
        
        manager = get_context_manager()
        assert manager.current_profile.name == "philosophical"
    
    def test_adjust_with_context_global(self):
        """adjust_with_context usa contexto global."""
        set_context_profile("technical")
        
        sem = [0.5] * FIXED_DIMS
        unc = [0.2] * FIXED_DIMS
        
        adjusted_sem, adjusted_unc = adjust_with_context(sem, unc, context_alpha=0.2)
        
        assert len(adjusted_sem) == FIXED_DIMS
        assert len(adjusted_unc) == FIXED_DIMS


class TestContextIntegration:
    """Testes de integração com bridge."""
    
    @pytest.mark.asyncio
    async def test_projection_with_context(self):
        """Projeção usando contexto."""
        from leet.bridge import MockProjector
        from leet import encode
        
        manager = ContextManager()
        manager.set_profile("emergency")
        
        projector = MockProjector()
        
        # Projeta texto
        cogon = await encode("Servidor caiu", projector)
        
        # Adiciona ao histórico
        manager.add_to_history(cogon)
        
        # Verifica que contexto existe
        context = manager.get_context_cogon()
        assert context is not None
