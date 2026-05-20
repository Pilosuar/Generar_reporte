import openpyxl
from django.shortcuts import redirect, render
from django.http import HttpResponse
from google_auth_oauthlib.flow import Flow
from django.conf import settings
import os
from django.db.models import Count, Avg, F
from googleapiclient.errors import HttpError
import time
#Generar reportes


from generar_reporte.models import Alumno, Actividad, Materia, AlumnoMateria
from .google_classroom import sync_classroom_data
#http://127.0.0.1:8000/reporte/login
#http://127.0.0.1:8000/reporte/generar
#http://127.0.0.1:8000/reporte/iniciar
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]


# VISTA INICIAL
def index(request):
    return render(request, "index.html")

# VISTA PARA INICIAR SESION CON UNA CUENTA DE GOOGLE
def login_google(request):
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri="http://127.0.0.1:8000/reporte/generar"
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    # GUAREDAR EL 'code_verifier' EN LA SESIÓN
    request.session['code_verifier'] = flow.code_verifier
    return redirect(auth_url)

# VISTA QUE REECIBE EL CALLBACK, GUARDA EL TOKEN Y ALMACENA LOS DATOS DE CLASSROOM
def generar_callback(request):
    code = request.GET.get("code")
    error = request.GET.get("error")
    if error:
        return HttpResponse(f"Error en login: {error}")
    if code:
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri="http://127.0.0.1:8000/reporte/generar"
        )
        # RECUPERA EL 'code_verifier'
        flow.code_verifier = request.session.get('code_verifier')
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_path = settings.BASE_DIR / "credentials" / "token.json"
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    # EN CASO DE PODER CONECTAR CON CLASSROOM INTENTAR 3 VECES O ENVIAR A UNA PANTALLA DE ERROR
    intentos = 3
    for i in range(intentos):
        try:
            sync_classroom_data()
            break  # si funciona, salimos del bucle
        except HttpError as e:
            if e.resp.status == 503:
                if i < intentos - 1:
                    # Esperar 5 segundos y volver a intentar
                    time.sleep(5)
                    continue
                else:
                    mensaje = []
                    return redirect(" url 'reporte/error' ")
    
    return render(request, "continuar.html")

# Panatalla de error para el caso 'error 503' (no conexion con classroom)
def error_503(request):
    return render(request, "error_503.html")

#def error_404(reuqest):
    #return render(reuqest, "error_404.html")

#### VISTA DE 'generar_reporte.html'
def reporte_alumno(request):  
    # Consulta que trae todos los alumnos con sus relaciones
    alumnos = Alumno.objects.prefetch_related(
        "alumnomateria_set__materia",
        "alumnomateria_set__materia__actividad_set"
    )

    datos = []
    for alumno in alumnos:
        materias_info = []
        for relacion in alumno.alumnomateria_set.all():
            actividades = Actividad.objects.filter(
                alumno=alumno,
                materia=relacion.materia
            )

            total = actividades.count()
            entregadas = actividades.filter(actividad_entregada=True).count()
            porcentaje = (entregadas / total * 100) if total > 0 else 0
            promedio = actividades.aggregate(promedio=Avg("calificacion"))["promedio"] or 0

            materias_info.append({
                "materia": relacion.materia.nombre,
                "promedio": round(promedio, 2),
                "entregadas": entregadas,
                "total": total,
                "porcentaje": porcentaje,
                "actividades_no_entregadas": actividades.filter(actividad_entregada=False),
                "calificaciones": actividades.values_list("calificacion", flat=True)
            })

        datos.append({
            "id": alumno.id,
            "alumno": alumno.nombre_completo,
            "materias": materias_info
        })

    return render(request, "reportes_alumnos.html", {
        "alumnos_realcion": alumnos,
        "datos": datos
    })
    
def alumno_buscado(request):
    # Capturar la búsqueda
    buscar = request.GET["buscar"]

    # Filtrar alumnos por nombre
    alumnos = Alumno.objects.filter(nombre_completo__icontains=buscar).prefetch_related(
        "alumnomateria_set__materia",
        "alumnomateria_set__materia__actividad_set"
    )

    datos = []
    for alumno in alumnos:
        materias_info = []
        for relacion in alumno.alumnomateria_set.all():
            actividades = Actividad.objects.filter(
                alumno=alumno,
                materia=relacion.materia
            )
            total = actividades.count()
            entregadas = actividades.filter(actividad_entregada=True).count()
            porcentaje = (entregadas / total * 100) if total > 0 else 0
            promedio = actividades.aggregate(promedio=Avg("calificacion"))["promedio"] or 0

            materias_info.append({
                "materia": relacion.materia.nombre,
                "promedio": round(promedio, 2),
                "entregadas": entregadas,
                "total": total,
                "porcentaje": porcentaje,
                "actividades_no_entregadas": actividades.filter(actividad_entregada=False),
            })

        datos.append({
            "id": alumno.id,
            "alumno": alumno.nombre_completo,
            "materias": materias_info,
        })

    # Renderizar otro HTML con los resultados
    return render(request, "buscar_alumno.html", {
        "datos": datos,
        "buscar": buscar,
    })

## HTML del reporte general #   
def reporte_materia(request):
    # Traer todas las materias con sus relaciones
    materias = Materia.objects.prefetch_related(
        "alumnomateria_set__alumno",
        "actividad_set"
    )

    datos = []
    materias_unicas = set()

    for materia in materias:
        alumnos_info = []
        for relacion in materia.alumnomateria_set.all():
            alumno = relacion.alumno

            # Filtrar actividades por alumno y materia
            actividades = Actividad.objects.filter(
                alumno=alumno,
                materia=materia
            )

            # Calcular promedio
            promedio = actividades.aggregate(promedio=Avg("calificacion"))["promedio"] or 0

            alumnos_info.append({
            "alumno": alumno.nombre_completo,
            "calificaciones": list(actividades.values_list("calificacion", flat=True)),
            "nombres_actividades": list(actividades.values_list("nombre_materias_no_entregadas", flat=True)),
            "promedio": round(promedio, 2),
            })

        datos.append({
            "materia": materia.nombre,
            "alumnos": alumnos_info
        })

        # Agregar materia al conjunto de únicas
        materias_unicas.add(materia.nombre)

    # Convertir a lista ordenada
    materias_unicas = sorted(list(materias_unicas))

    # Renderizar template con contexto completo
    return render(request, "reportes_materias.html", {
        "datos": datos,
        "materias_unicas": materias_unicas
    })
      
def materia_buscada(request):
    materia_nombre = request.GET.get("materia")
    datos = []

    if materia_nombre:
        materia = Materia.objects.prefetch_related(
            "alumnomateria_set__alumno",
            "actividad_set"
        ).filter(nombre=materia_nombre).first()

        if materia:
            alumnos_info = []
            for relacion in materia.alumnomateria_set.all():
                alumno = relacion.alumno

                actividades = Actividad.objects.filter(
                    alumno=alumno,
                    materia=materia
                )

                promedio = actividades.aggregate(promedio=Avg("calificacion"))["promedio"] or 0

                alumnos_info.append({
                    "alumno": alumno.nombre_completo,
                    "calificaciones": list(actividades.values_list("calificacion", flat=True)),
                    "nombres_actividades": list(actividades.values_list("nombre_materias_no_entregadas", flat=True)),
                    "promedio": round(promedio, 2),
                })

            datos.append({
                "materia": materia.nombre,
                "alumnos": alumnos_info
            })

    # Siempre se devuelve el mismo template, con datos llenos o vacíos
    return render(request, "buscar_materia.html", {
        "buscar": materia_nombre,
        "datos": datos
    })

def generar_reporte_alumno(request, alumno_id):
    alumno = Alumno.objects.get(id=alumno_id)
    relaciones = AlumnoMateria.objects.filter(alumno=alumno).select_related("materia")

    # Crear workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"

    # Encabezados
    ws.append(["Alumno", "Materia", "Promedio", "Entregadas", "Total", "Porcentaje de entrega"])

    for relacion in relaciones:
        materia = relacion.materia
        actividades = Actividad.objects.filter(alumno=alumno, materia=materia)

        total = actividades.count()
        entregadas = actividades.filter(actividad_entregada=True).count()
        porcentaje = (entregadas / total * 100) if total > 0 else 0
        promedio = actividades.aggregate(promedio=Avg("calificacion"))["promedio"] or 0

        ws.append([
            alumno.nombre_completo,
            materia.nombre,
            round(promedio, 2),
            entregadas,
            total,
            round(porcentaje, 2)
        ])

    # Respuesta HTTP con archivo XLSX
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="reporte_{alumno.nombre_completo}.xlsx"'
    wb.save(response)
    return response