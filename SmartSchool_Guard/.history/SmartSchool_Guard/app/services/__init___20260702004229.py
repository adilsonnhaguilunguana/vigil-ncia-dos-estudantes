"""
Pacote de serviços do SmartSchool Guard.

Contém a lógica de negócio principal:
- Cadastro de alunos com verificação de qualidade de foto
- Reconhecimento facial em tempo real
- Detecção de cruzamento de linha virtual
- Envio de notificações WhatsApp/SMS
- Comunicação com ESP8266
- Funções utilitárias
"""

from app.services.cadastro import CadastroAluno
from app.services.reconhecimento import ReconhecimentoFacial, init_reconhecimento
from app.services.zona_deteccao import ZonaDeteccao
from app.services.notificacoes import Notificador
from app.services.esp_controlo import ESPControlo