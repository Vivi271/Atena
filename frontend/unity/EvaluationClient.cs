using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// Cliente HTTP para comunicar la aplicación Unity (NeuroK AR / Atena)
/// con el módulo de evaluación de la API de Atena desplegada en Render (o local).
/// Consulta el banco de preguntas normalizado almacenado en Supabase/PostgreSQL.
/// </summary>
public class EvaluationClient : MonoBehaviour
{
    [Header("Configuración de Red")]
    [Tooltip("URL base de la API de Atena en Render")]
    public string baseUrl = "https://atena-vugz.onrender.com";

    [Tooltip("Tiempo de espera máximo para la petición en segundos")]
    public int timeoutSeconds = 30;

    // Instancia Singleton para acceso global
    public static EvaluationClient Instance { get; private set; }

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }

    #region Estructuras de Datos JSON

    [Serializable]
    public class RespuestaData
    {
        public int id;
        public string texto;
        public bool es_correcta;
    }

    [Serializable]
    public class PreguntaData
    {
        public int id;
        public string enunciado;
        public string tema;
        public string nivel;
        public List<RespuestaData> respuestas;
    }

    [Serializable]
    public class PreguntasEvaluacionResponse
    {
        public string nivel;
        public int cantidad;
        public List<PreguntaData> preguntas;
    }

    #endregion

    /// <summary>
    /// Consulta el banco de preguntas de autoevaluación filtrando por nivel pedagógico.
    /// </summary>
    /// <param name="nivel">"basico" o "avanzado"</param>
    /// <param name="cantidad">Cantidad opcional de preguntas (ej. 5 o 15). Si es 0 o menor, trae todas.</param>
    /// <param name="aleatorio">Si es true, el servidor entrega preguntas en orden aleatorio</param>
    /// <param name="onSuccess">Callback con la respuesta deserializada</param>
    /// <param name="onError">Callback con mensaje de error</param>
    public void ObtenerPreguntas(
        string nivel,
        int cantidad,
        bool aleatorio,
        Action<PreguntasEvaluacionResponse> onSuccess,
        Action<string> onError)
    {
        StartCoroutine(ObtenerPreguntasCoroutine(nivel, cantidad, aleatorio, onSuccess, onError));
    }

    private IEnumerator ObtenerPreguntasCoroutine(
        string nivel,
        int cantidad,
        bool aleatorio,
        Action<PreguntasEvaluacionResponse> onSuccess,
        Action<string> onError)
    {
        string nivelParam = string.IsNullOrEmpty(nivel) ? "avanzado" : nivel.ToLower();
        string url = $"{baseUrl}/api/evaluacion/preguntas?nivel={UnityWebRequest.EscapeURL(nivelParam)}&aleatorio={aleatorio.ToString().ToLower()}";

        if (cantidad > 0)
        {
            url += $"&cantidad={cantidad}";
        }

        Debug.Log($"[EvaluationClient] Solicitando preguntas a: {url}");

        using (UnityWebRequest webRequest = UnityWebRequest.Get(url))
        {
            webRequest.timeout = timeoutSeconds;
            webRequest.SetRequestHeader("Accept", "application/json");

            yield return webRequest.SendWebRequest();

            if (webRequest.result == UnityWebRequest.Result.ConnectionError ||
                webRequest.result == UnityWebRequest.Result.ProtocolError)
            {
                string errorMsg = $"Error ({webRequest.responseCode}): {webRequest.error}";
                Debug.LogError($"[EvaluationClient] {errorMsg}");
                onError?.Invoke(errorMsg);
            }
            else
            {
                string jsonResponse = webRequest.downloadHandler.text;
                Debug.Log($"[EvaluationClient] Respuesta recibida: {jsonResponse}");

                try
                {
                    PreguntasEvaluacionResponse response = JsonUtility.FromJson<PreguntasEvaluacionResponse>(jsonResponse);

                    if (response == null || response.preguntas == null || response.preguntas.Count == 0)
                    {
                        onError?.Invoke("No se encontraron preguntas para el nivel seleccionado.");
                        yield break;
                    }

                    onSuccess?.Invoke(response);
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[EvaluationClient] Error al deserializar JSON: {ex.Message}");
                    onError?.Invoke("Error al procesar el formato de preguntas del servidor.");
                }
            }
        }
    }

    /// <summary>
    /// Utilidad estática para mezclar (shuffle) una lista (por ejemplo, las 4 opciones de respuesta)
    /// usando el algoritmo Fisher-Yates para asegurar aleatoriedad en la UI.
    /// </summary>
    public static void MezclarLista<T>(IList<T> lista)
    {
        if (lista == null || lista.Count <= 1) return;
        System.Random rng = new System.Random();
        int n = lista.Count;
        while (n > 1)
        {
            n--;
            int k = rng.Next(n + 1);
            T value = lista[k];
            lista[k] = lista[n];
            lista[n] = value;
        }
    }
}
