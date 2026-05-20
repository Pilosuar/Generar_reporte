import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from django.conf import settings
from generar_reporte.models import Alumno, AlumnoMateria, Actividad, Materia, Profesor, MateriaProfesor

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]

def get_service():
    token_path = settings.BASE_DIR / "credentials" / "token.json"
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("classroom", "v1", credentials=creds)

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

### almacena en la base de datos
def sync_classroom_data():
    service = get_service()
    courses = service.courses().list().execute().get("courses", [])
    for course in courses:
        # Guardamos el nombre y el ID de la clase
        materia_obj, _ = Materia.objects.update_or_create(
            google_id=course.get("id"),   # ID único de la clase en Classroom
            defaults={"nombre": course.get("name", "Sin nombre")}
        )

        # 🔹 Traer profesor de la clase (requiere scope classroom.profile.emails)
        teacher_list = service.courses().teachers().list(courseId=course["id"]).execute().get("teachers", [])
        for teacher in teacher_list:
            profile = teacher.get("profile", {})
            nombre_profesor = profile.get("name", {}).get("fullName", "Sin nombre")
            google_id_profesor = profile.get("id", None)
            correo_profesor = profile.get("emailAddress", None)  # ahora sí disponible con el scope correcto

            profesor_obj, _ = Profesor.objects.update_or_create(
                google_id=google_id_profesor,
                defaults={
                    "nombre_completo": nombre_profesor,
                    "correo": correo_profesor  # puede ser None si no viene
                }
            )

            # Relación profesor-materia
            MateriaProfesor.objects.update_or_create(
                profesor=profesor_obj,
                materia=materia_obj
            )

        # 🔹 Traer estudiantes de la clase
        students = service.courses().students().list(courseId=course["id"]).execute().get("students", [])
        for student in students:
            profile = student.get("profile", {})
            nombre = profile.get("name", {}).get("fullName", "Sin nombre")
            google_id = profile.get("id", None)

            alumno_obj, _ = Alumno.objects.update_or_create(
                google_id=google_id,
                defaults={"nombre_completo": nombre}
            )

            # Relación alumno-materia
            AlumnoMateria.objects.update_or_create(
                alumno=alumno_obj,
                materia=materia_obj
            )

            # 🔹 Recorrer las tareas del curso
            coursework = service.courses().courseWork().list(courseId=course["id"]).execute().get("courseWork", [])
            for work in coursework:
                submissions = service.courses().courseWork().studentSubmissions().list(
                    courseId=course["id"],
                    courseWorkId=work["id"]
                ).execute().get("studentSubmissions", [])

                entregada = False
                grade = 0
                for sub in submissions:
                    if sub.get("userId") == google_id:
                        grade = sub.get("assignedGrade", 0)
                        entregada = sub.get("state") in ["RETURNED"]

                # Guardar/actualizar actividad
                Actividad.objects.update_or_create(
                    alumno=alumno_obj,
                    materia=materia_obj,
                    nombre_materias_no_entregadas=work.get("title", "Sin título"),
                    defaults={
                        "actividad_entregada": entregada,
                        "calificacion": grade
                    }
                )

