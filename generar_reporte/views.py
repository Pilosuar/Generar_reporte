from django.shortcuts import redirect, render
from django.http import HttpResponse
from google_auth_oauthlib.flow import Flow
from django.conf import settings
import os
from django.db.models import Count, Avg, F

from generar_reporte.models import Alumno, Actividad
from .google_classroom import sync_classroom_data
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
    # Sincroniza datos primero
    sync_classroom_data()
    
    # Trae todos los alumnos con sus relaciones
    alumnos = Alumno.objects.prefetch_related(
        "alumnomateria_set__materia",
        "alumnomateria_set__materia__actividad_set"
    )

    datos = []
    for alumno in alumnos:
        materias_info = []
        for relacion in alumno.alumnomateria_set.all():
            # 🔹 Filtrar actividades por alumno y materia
            actividades = Actividad.objects.filter(
                alumno=alumno,
                materia=relacion.materia
            )

            total = actividades.count()
            entregadas = actividades.filter(actividad_entregada=True).count()
            porcentaje = (entregadas / total * 100) if total > 0 else 0

            # Calcular promedio de calificaciones
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
            "alumno": alumno.nombre_completo,
            "materias": materias_info
        })
  
    return render(request,"generar_reporte.html",
                  {"alumnos_realcion": alumnos,
                   "datos": datos})
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