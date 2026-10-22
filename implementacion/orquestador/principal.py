"""Arranque del orquestador.

Ejemplos:
  python -m orquestador --simular                 impresora, camara y modelo simulados; Telegram real
  python -m orquestador --simular --consola       todo simulado, mensajes en consola
  python -m orquestador --simular-modelo          impresora y camara reales; modelo con respuestas fijas
  python -m orquestador                           todo real (requiere .env completo y la clave de OpenAI)
  python -m orquestador --registrar-operador ...  el primer /start privado queda como operador autorizado
"""
import argparse
import logging
import sys
from types import SimpleNamespace

from .agente import Agente, AgenteSimulado
from .camara import CamaraA1, CamaraSimulada
from .config import RAIZ, guardar_en_env, leer_config
from .impresora import ImpresoraMQTT, ImpresoraSimulada
from .microcontrolador import MicrocontroladorSimulado
from .orquestador import Orquestador
from .registro import Registro
from .servidor_funciones import Funciones, crear_servidor
from .telegram_bot import Telegram, TelegramConsola


def construir(config, simular=False, simular_modelo=False, consola=False, guion=None,
              escala=60.0, registrar_operador=False, base_datos=None):
    """Arma el sistema; con simular=True no toca ni la impresora ni la camara."""
    if simular:
        impresora = ImpresoraSimulada(escala=escala)
        camara = CamaraSimulada(RAIZ / "pruebas" / "imagenes")
    else:
        if not config.impresora_configurada:
            sys.exit("Faltan IMPRESORA_IP, IMPRESORA_SERIE o IMPRESORA_CODIGO_ACCESO en .env")
        impresora = ImpresoraMQTT(config.impresora_ip, config.serie, config.codigo_acceso)
        impresora.conectar()
        camara = CamaraA1(config.impresora_ip, config.codigo_acceso)

    if consola:
        telegram = TelegramConsola(guion)
    else:
        if not config.telegram_token:
            sys.exit("Falta TELEGRAM_TOKEN en .env")
        al_registrar = (lambda i: guardar_en_env("TELEGRAM_OPERADOR_ID", str(i))) if registrar_operador else None
        telegram = Telegram(config.telegram_token, config.operador_id, al_registrar)

    registro = Registro(base_datos or config.carpeta_datos / "registro.sqlite")
    sistema = SimpleNamespace(config=config, impresora=impresora, camara=camara,
                              telegram=telegram, registro=registro)
    micro = MicrocontroladorSimulado(impresora, lambda t, d: sistema.orquestador.evento_micro(t, d),
                                     escala=escala if simular else 1.0)
    micro.espera_verificacion = config.plazo_confirmacion
    funciones = Funciones(config, impresora, camara, telegram, registro, micro,
                          lambda a, m: sistema.orquestador._solicitar(a, m))
    servidor = crear_servidor(funciones)
    agente = (AgenteSimulado(servidor=servidor) if (simular or simular_modelo)
              else Agente(config.modelo, servidor))
    sistema.micro, sistema.funciones, sistema.servidor, sistema.agente = micro, funciones, servidor, agente
    sistema.orquestador = Orquestador(config, impresora, camara, telegram, registro, micro, agente, funciones)
    return sistema


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="orquestador", description="Orquestador del sistema para la A1 mini")
    p.add_argument("--simular", action="store_true", help="impresora, camara y modelo simulados")
    p.add_argument("--simular-modelo", action="store_true", help="solo el modelo con respuestas fijas")
    p.add_argument("--consola", action="store_true", help="Telegram sustituido por la consola")
    p.add_argument("--registrar-operador", action="store_true",
                   help="el primer /start privado queda como operador autorizado")
    p.add_argument("--imprimir-prueba", action="store_true",
                   help="en simulacion, arranca una impresion simulada de 20 min")
    p.add_argument("--duracion", type=float, default=None, help="segundos de ejecucion")
    a = p.parse_args(argv)

    config = leer_config()
    config.carpeta_datos.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(config.carpeta_datos / "orquestador.log", encoding="utf-8")])
    if a.simular:
        # En simulacion el tiempo corre 60 veces mas rapido: 10 min de supervision son 10 s.
        config.periodo_supervision /= 60
        config.recordatorio_pausa /= 60
    sistema = construir(config, simular=a.simular, simular_modelo=a.simular_modelo, consola=a.consola,
                        registrar_operador=a.registrar_operador)
    if a.simular:
        # La pieza simulada sale de la plataforma al evacuar, para que la verificacion la vea libre.
        sistema.micro.al_evacuar = lambda: setattr(sistema.camara, "escena", "plataforma_vacia")
        if a.imprimir_prueba:
            sistema.impresora.iniciar_impresion()
    logging.getLogger("principal").info(
        "Orquestador en marcha. Bot: %s. Operador: %s. Impresora: %s. Modelo: %s.",
        sistema.telegram.identidad().get("username"), config.operador_id or "sin registrar",
        "simulada" if a.simular else config.impresora_ip,
        "simulado" if (a.simular or a.simular_modelo) else config.modelo)
    try:
        sistema.orquestador.ejecutar(a.duracion)
    except KeyboardInterrupt:
        pass
    finally:
        sistema.orquestador.detener()
        sistema.impresora.cerrar()


if __name__ == "__main__":
    main()
