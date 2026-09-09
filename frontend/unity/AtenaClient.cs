using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// Cliente HTTP para comunicar la aplicación de Unity (NeuroK AR) 
/// con la API de Atena (RAG de Neuroanatomía) desplegada en Render.
/// </summary>
public class AtenaClient : MonoBehaviour
{
    [Header("Configuración del Servidor")]
    [Tooltip("URL pública de la API de Atena en Render")]
    public string baseUrl = "https://atena-vugz.onrender.com";

    // Instancia Singleton para acceso global fácil desde cualquier script o UI
    public static AtenaClient Instance { get; private set; }

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
    public class ConsultaRequest
    {
        public string pregunta;
        public string nivel = "avanzado"; // "basico" | "avanzado"
        public int k = 6;
    }

    [Serializable]
    public class FuenteResponse
    {
        public string fuente;
        public int pagina;
        public string fragmento;
    }

    [Serializable]
    public class ConsultaResponse
    {
        public string respuesta;
        public List<FuenteResponse> fuentes;
        public string nivel;
    }

    #endregion

    /// <summary>
    /// Envía una pregunta al Asistente IA de Atena y ejecuta callbacks al recibir la respuesta o error.
    /// </summary>
    /// <param name="pregunta">Texto de la consulta del usuario</param>
    /// <param name="nivel">"basico" o "avanzado"</param>
    /// <param name="onSuccess">Callback ejecutado cuando la respuesta llega exitosamente</param>
    /// <param name="onError">Callback ejecutado si ocurre un error de red o de servidor</param>
    public void ConsultarAsistente(string pregunta, string nivel, Action<ConsultaResponse> onSuccess, Action<string> onError)
    {
        if (string.IsNullOrEmpty(pregunta) || string.IsNullOrEmpty(pregunta.Trim()))
        {
            onError?.Invoke("La pregunta no puede estar vacía.");
            return;
        }

        StartCoroutine(EnviarConsultaCoroutine(pregunta.Trim(), nivel, onSuccess, onError));
    }

    private IEnumerator EnviarConsultaCoroutine(string pregunta, string nivel, Action<ConsultaResponse> onSuccess, Action<string> onError)
    {
        string endpoint = $"{baseUrl}/consultar";

        ConsultaRequest requestData = new ConsultaRequest
        {
            pregunta = pregunta,
            nivel = string.IsNullOrEmpty(nivel) ? "basico" : nivel.ToLower(),
            k = 6
        };

        string jsonPayload = JsonUtility.ToJson(requestData);
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonPayload);

        using (UnityWebRequest webRequest = new UnityWebRequest(endpoint, "POST"))
        {
            webRequest.uploadHandler = new UploadHandlerRaw(bodyRaw);
            webRequest.downloadHandler = new DownloadHandlerBuffer();
            webRequest.SetRequestHeader("Content-Type", "application/json");
            webRequest.timeout = 35; // Timeout en segundos

            yield return webRequest.SendWebRequest();

            if (webRequest.result == UnityWebRequest.Result.ConnectionError || 
                webRequest.result == UnityWebRequest.Result.ProtocolError)
            {
                string errorMsg = $"Error ({webRequest.responseCode}): {webRequest.error}";
                Debug.LogError($"[AtenaClient] {errorMsg}");
                onError?.Invoke(errorMsg);
            }
            else
            {
                string jsonResponse = webRequest.downloadHandler.text;
                Debug.Log($"[AtenaClient] Respuesta recibida del servidor: {jsonResponse}");

                try
                {
                    ConsultaResponse response = JsonUtility.FromJson<ConsultaResponse>(jsonResponse);
                    onSuccess?.Invoke(response);
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[AtenaClient] Error al deserializar JSON: {ex.Message}");
                    onError?.Invoke("Error al procesar el formato de la respuesta del servidor.");
                }
            }
        }
    }
}
