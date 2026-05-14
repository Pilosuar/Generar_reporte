import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from django.conf import settings
from generar_reporte.models import Alumno, AlumnoMateria, MateriaActividad, Materia

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly"
]

def get_service():
    token_path = settings.BASE_DIR / "credentials" / "token.json"
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("classroom", "v1", credentials=creds)

def get_courses():
    service = get_service()
    results = service.courses().list(pageSize=10).execute()
    return results.get("courses", [])

def exchange_code_for_token(code, code_verifier=None):
    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri="http://127.0.0.1:8000/reporte/generar"
    )
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_path = settings.BASE_DIR / "credentials" / "token.json"
    with open(token_path, "w") as token:
        token.write(creds.to_json())

def get_students(course_id):
    service = get_service()
    results = service.courses().students().list(courseId=course_id).execute()
    return results.get("students", [])


### almacena en la base de datos
def sync_classroom_data():
    service = get_service()
    courses = service.courses().list().execute().get("courses", [])
    for course in courses:
        materia_obj, _ = Materia.objects.get_or_create(
            nombre=course.get("name", "Sin nombre")
        )
        students = service.courses().students().list(courseId=course["id"]).execute().get("students", [])
        for student in students:
            profile = student.get("profile", {})
            nombre = profile.get("name", {}).get("fullName", "Sin nombre")
            alumno_obj, _ = Alumno.objects.get_or_create(
                nombre_completo=nombre,
                materia=materia_obj.nombre
            )
            AlumnoMateria.objects.get_or_create(
                alumno=alumno_obj,
                materia=materia_obj,
                calificacion=0
            )
### verifica si esta entregada o no
def sync_activities(course_id):
    service = get_service()
    coursework = service.courses().courseWork().list(courseId=course_id).execute().get("courseWork", [])
    course = service.courses().get(id=course_id).execute()
    materia_obj = Materia.objects.get(nombre=course.get("name", "Sin nombre"))
    for work in coursework:
        entregada = work.get("state") == "TURNED_IN"
        MateriaActividad.objects.create(
            materia=materia_obj,
            actividad_entregada=entregada,
            nombre_materias_no_entregadas=work.get("title", "Sin título")
        )
