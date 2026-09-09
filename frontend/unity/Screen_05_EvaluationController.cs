using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

/// <summary>
/// Controlador de interfaz gráfica para la pantalla de evaluación (Screen_05_Evaluation) en Unity.
/// Maneja la carga de preguntas vía EvaluationClient, barajado de opciones,
/// navegación interactiva y visualización del resumen de aciertos final.
/// </summary>
public class Screen_05_EvaluationController : MonoBehaviour
{
    [Header("Configuración de Nivel")]
    [Tooltip("Nivel actual a evaluar: 'basico' o 'avanzado'")]
    public string nivel = "avanzado";
    [Tooltip("Cantidad de preguntas (15 por defecto, o 0 para todas)")]
    public int cantidadPreguntas = 15;
    [Tooltip("Mezclar preguntas del examen")]
    public bool aleatorio = true;

    [Header("Referencias de UI - Panel de Preguntas")]
    public GameObject panelQuiz;
    public TMP_Text txtContadorPregunta;    // Ej: "Pregunta 1 de 15"
    public TMP_Text txtTema;                // Ej: "Vías Sensitivas"
    public TMP_Text txtEnunciado;           // Texto de la pregunta
    public Button[] botonesOpciones;        // 4 botones (A, B, C, D)
    public TMP_Text[] textosOpciones;       // Textos de los 4 botones
    public GameObject panelCargando;

    [Header("Referencias de UI - Panel de Resultados")]
    public GameObject panelResultados;
    public TMP_Text txtPuntajeFinal;        // Ej: "12 / 15 aciertos"
    public TMP_Text txtPorcentaje;          // Ej: "80%"
    public TMP_Text txtMensajeFeedback;     // Felicitaciones o sugerencia de repaso
    public Button btnReiniciar;

    // Estado interno
    private List<EvaluationClient.PreguntaData> listaPreguntas = new List<EvaluationClient.PreguntaData>();
    private int indicePreguntaActual = 0;
    private int aciertos = 0;
    private bool esperandoRespuesta = false;

    private void Start()
    {
        if (btnReiniciar != null)
        {
            btnReiniciar.onClick.AddListener(IniciarEvaluacion);
        }

        // Asignar listeners a los botones de opción
        for (int i = 0; i < botonesOpciones.Length; i++)
        {
            int index = i;
            botonesOpciones[i].onClick.AddListener(() => OnOpcionSeleccionada(index));
        }

        IniciarEvaluacion();
    }

    /// <summary>
    /// Inicia o reinicia la sesión de evaluación solicitando las preguntas a la API.
    /// </summary>
    public void IniciarEvaluacion()
    {
        aciertos = 0;
        indicePreguntaActual = 0;
        esperandoRespuesta = false;

        if (panelResultados != null) panelResultados.SetActive(false);
        if (panelQuiz != null) panelQuiz.SetActive(false);
        if (panelCargando != null) panelCargando.SetActive(true);

        // Asegurar existencia del cliente
        if (EvaluationClient.Instance == null)
        {
            gameObject.AddComponent<EvaluationClient>();
        }

        EvaluationClient.Instance.ObtenerPreguntas(
            nivel,
            cantidadPreguntas,
            aleatorio,
            onSuccess: (response) =>
            {
                if (panelCargando != null) panelCargando.SetActive(false);
                listaPreguntas = response.preguntas;

                if (listaPreguntas != null && listaPreguntas.Count > 0)
                {
                    if (panelQuiz != null) panelQuiz.SetActive(true);
                    MostrarPreguntaActual();
                }
                else
                {
                    Debug.LogWarning("[Screen_05_Evaluation] La lista de preguntas está vacía.");
                }
            },
            onError: (error) =>
            {
                if (panelCargando != null) panelCargando.SetActive(false);
                Debug.LogError($"[Screen_05_Evaluation] Error al cargar: {error}");
                if (txtEnunciado != null)
                {
                    txtEnunciado.text = $"<color=red>Error al conectar con la base de datos de evaluación:\n{error}</color>";
                }
                if (panelQuiz != null) panelQuiz.SetActive(true);
            }
        );
    }

    private void MostrarPreguntaActual()
    {
        if (indicePreguntaActual >= listaPreguntas.Count)
        {
            MostrarResultadosFinales();
            return;
        }

        esperandoRespuesta = true;
        var preguntaActual = listaPreguntas[indicePreguntaActual];

        // 1. Contador y encabezados
        if (txtContadorPregunta != null)
            txtContadorPregunta.text = $"Pregunta {indicePreguntaActual + 1} de {listaPreguntas.Count}";

        if (txtTema != null)
            txtTema.text = string.IsNullOrEmpty(preguntaActual.tema) ? "General" : preguntaActual.tema;

        if (txtEnunciado != null)
            txtEnunciado.text = preguntaActual.enunciado;

        // 2. Mezclar las 4 opciones para evitar sesgos de posición
        List<EvaluationClient.RespuestaData> opcionesMezcladas = new List<EvaluationClient.RespuestaData>(preguntaActual.respuestas);
        EvaluationClient.MezclarLista(opcionesMezcladas);

        // 3. Pintar opciones en los botones
        for (int i = 0; i < botonesOpciones.Length; i++)
        {
            if (i < opcionesMezcladas.Count)
            {
                botonesOpciones[i].gameObject.SetActive(true);
                botonesOpciones[i].interactable = true;

                // Guardar la opción en una variable temporal o componente si se requiere
                string prefijo = $"{(char)('A' + i)}. ";
                if (textosOpciones != null && i < textosOpciones.Length && textosOpciones[i] != null)
                {
                    textosOpciones[i].text = $"{prefijo}{opcionesMezcladas[i].texto}";
                }
            }
            else
            {
                botonesOpciones[i].gameObject.SetActive(false);
            }
        }

        // Guardar referencia a la lista mezclada actual para verificar el clic
        respuestasActualesMezcladas = opcionesMezcladas;
    }

    private List<EvaluationClient.RespuestaData> respuestasActualesMezcladas;

    private void OnOpcionSeleccionada(int indiceBoton)
    {
        if (!esperandoRespuesta || respuestasActualesMezcladas == null) return;
        esperandoRespuesta = false;

        // Deshabilitar botones temporalmente
        foreach (var btn in botonesOpciones)
        {
            if (btn != null) btn.interactable = false;
        }

        bool esCorrecta = false;
        if (indiceBoton < respuestasActualesMezcladas.Count)
        {
            esCorrecta = respuestasActualesMezcladas[indiceBoton].es_correcta;
        }

        if (esCorrecta)
        {
            aciertos++;
            Debug.Log($"[Quiz] ¡Correcto! Aciertos: {aciertos}");
        }
        else
        {
            Debug.Log("[Quiz] Incorrecto.");
        }

        // Pequeño retardo visual antes de pasar a la siguiente pregunta
        Invoke(nameof(SiguientePregunta), 0.5f);
    }

    private void SiguientePregunta()
    {
        indicePreguntaActual++;
        MostrarPreguntaActual();
    }

    private void MostrarResultadosFinales()
    {
        if (panelQuiz != null) panelQuiz.SetActive(false);
        if (panelResultados != null) panelResultados.SetActive(true);

        int total = listaPreguntas.Count;
        float porcentaje = total > 0 ? ((float)aciertos / total) * 100f : 0f;

        if (txtPuntajeFinal != null)
            txtPuntajeFinal.text = $"{aciertos} / {total} aciertos";

        if (txtPorcentaje != null)
            txtPorcentaje.text = $"{porcentaje:F0}%";

        if (txtMensajeFeedback != null)
        {
            if (porcentaje >= 80f)
                txtMensajeFeedback.text = "¡Excelente dominio neuroanatómico! Has superado la evaluación con distinción.";
            else if (porcentaje >= 60f)
                txtMensajeFeedback.text = "Buen desempeño. Te recomendamos repasar los temas con Atena para afianzar conceptos clave.";
            else
                txtMensajeFeedback.text = "Sigue practicando. Consulta a Atena sobre las estructuras que presentaron mayor dificultad.";
        }
    }
}
