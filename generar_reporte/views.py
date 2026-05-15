from django.shortcuts import redirect, render
from django.http import HttpResponse
from google_auth_oauthlib.flow import Flow
from django.conf import settings
import os
from django.db.models import Count, Avg, F

from generar_reporte.models import Alumno, AlumnoMateria, MateriaActividad, Materia
from .google_classroom import sync_classroom_data, sync_activities
#http://127.0.0.1:8000/reporte/generar
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
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

# VISTA QUE REECIBE EL CALLBACK Y GUARDA EL TOKEN
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
    return render(request, "continuar.html")

#### VISTA DE 'generar_reporte.html'
def generar_reporte(request):
    # FUNCIONES QUE ALMACENA TODOS LOS DATOS EN LA BASE DE DATOS
    # Sincroniza datos primero
    sync_classroom_data()
    sync_activities(course_id="863630393187")
    
    # Trae todos los alumnos con sus relaciones
    alumnos = Alumno.objects.prefetch_related(
        "alumnomateria_set__materia",
        "alumnomateria_set__materia__materiaactividad_set"
    )

    datos = []
    for alumno in alumnos:
        materias_info = []
        for relacion in alumno.alumnomateria_set.all():
            total = relacion.materia.materiaactividad_set.count()
            entregadas = relacion.materia.materiaactividad_set.filter(actividad_entregada=True).count()
            porcentaje = (entregadas / total * 100) if total > 0 else 0

            materias_info.append({
                "materia": relacion.materia.nombre,
                "calificacion": relacion.calificacion,
                "entregadas": entregadas,
                "total": total,
                "porcentaje": porcentaje,
                "actividades_no_entregadas": relacion.materia.materiaactividad_set.filter(actividad_entregada=False)
            })

        datos.append({
            "alumno": alumno.nombre_completo,
            "materias": materias_info
        })
  

    # SE SUSTITUIRÁ POR UNA CONSULTA EN BASE DE DATOS
    #OBTIENE LOS ALUMNOS DESDE CLASSROOM
    #students = get_students("863630393187")  # ID del curso
    #################################################################################################
    ## CONTINUAR CON EL CÓDIGO ->     
    return render(request,"generar_reporte.html", {"alumnos_realcion": alumnos,
                                                   "datos":datos})
    
### SE COLOCARÁ DENTRO DE GENARAR REPORTE (NO SERÁ UN 'INCLUDE')

    if request.method == "GET":
        if request.GET["busqueda"]:
            busqueda = request.GET["busqueda"]
            if len(busqueda)>20:
            #mensaje = "Articulo buscado: %r" %request.GET["producto"]
                mensaje = "Busqueda demasiado larga"
            else:
                busqueda= request.GET["busqueda"]
                alumnos_buscados = Alumno.objects.filter(nombre__icontains = busqueda)
                mensaje = []
    #################################################################################################
    ## CONTINUAR CON EL CÓDIGO ->
            return render(request,"generar_reporte.html", {"alumnos": alumnos_buscados, "mensaje":mensaje, "alumno_buscado":busqueda})
    return render(request, "barra_busqueda.html")