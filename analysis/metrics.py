from typing import Union
import numpy as np
import pandas as pd

# Tipos aceitos para permitir processamento escalar ou vetorial em séries temporais
NumericArray = Union[float, int, np.ndarray, pd.Series]


def calcular_fator_carga(
    demanda_media_kw: NumericArray, demanda_maxima_kw: NumericArray
) -> NumericArray:
  """Calcula o Fator de Carga (FC = Demanda Média / Demanda Máxima).

  Indica a eficiência do uso da potência instalada no período faturado.
  """
  # Evita divisão por zero convertendo denominadores nulos ou negativos para NaN/0
  demanda_max = np.maximum(demanda_maxima_kw, 0.0)

  # Aplica divisão vetorial segura com NumPy
  with np.errstate(divide="ignore", invalid="ignore"):
    fc = np.where(demanda_max > 0, demanda_media_kw / demanda_max, 0.0)

  # Retorna o tipo nativo float caso a entrada seja um número isolado
  return float(fc) if np.isscalar(fc) else fc


def calcular_ultrapassagem_demanda(
    demanda_medida_kw: NumericArray, demanda_contratada_kw: float
) -> NumericArray:
  """Calcula a parcela de ultrapassagem de demanda faturável.

  Aplica a margem de tolerância regulamentada de 5% sobre a demanda contratada
  (ANEEL).
  """
  if demanda_contratada_kw <= 0:
    raise ValueError("A demanda contratada deve ser um valor positivo em kW.")

  # Tolerância regulamentar de 5% (1.05 * Demanda Contratada)
  limite_tolerancia = demanda_contratada_kw * 1.05

  # Retorna a diferença apenas para medições que superaram o limite de tolerância
  excesso = np.maximum(0.0, demanda_medida_kw - limite_tolerancia)

  return float(excesso) if np.isscalar(excesso) else excesso


def calcular_custo_ultrapassagem_copel(
    demanda_medida_kw: NumericArray,
    demanda_contratada_kw: float,
    tarifa_demanda_rs_kw: float,
) -> NumericArray:
  """Calcula a penalidade financeira por ultrapassagem de demanda (Grupo A4 COPEL).

  Pela regra regulatória, a demanda excedente é cobrada com tarifa duplicada
  (2x).
  """
  kw_excedente = calcular_ultrapassagem_demanda(
      demanda_medida_kw, demanda_contratada_kw
  )

  # Multa regulamentar por ultrapassagem = Excesso (kW) * Tarifa de Demanda * 2
  custo_penalidade = kw_excedente * (tarifa_demanda_rs_kw * 2.0)

  return (
      float(custo_penalidade)
      if np.isscalar(custo_penalidade)
      else custo_penalidade
  )


def calcular_fator_demanda(
    demanda_maxima_kw: NumericArray, potencia_instalada_kw: float
) -> NumericArray:
  """Calcula o Fator de Demanda (FD = Demanda Máxima / Potência Instalada).

  Avalia o grau de simultaneidade das cargas elétricas da instalação.
  """
  if potencia_instalada_kw <= 0:
    return 0.0

  fd = demanda_maxima_kw / potencia_instalada_kw
  return float(fd) if np.isscalar(fd) else fd