from django.db import models

class Alumno(models.Model):
    nombre_completo = models.CharField(max_length=200)
    google_id = models.CharField(max_length=50,  unique=True, default=0)  # google_id

    def __str__(self):
        return self.nombre_completo

class Materia(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    google_id = models.CharField(max_length=50,  unique=True, default=0)
    def __str__(self):
        return self.nombre

class AlumnoMateria(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ("alumno", "materia")  # evita duplicados

class Actividad(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, default=0)   # alumno_id  FK
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)   # materia_id FK
    actividad_entregada = models.BooleanField(default=False)
    calificacion = models.IntegerField(default=0)
    nombre_materias_no_entregadas = models.CharField(max_length=200)

    class Meta:
        unique_together = ("alumno", "materia", "nombre_materias_no_entregadas")

class Profesor(models.Model):
    nombre_completo = models.CharField(max_length=200)
    correo = models.EmailField(unique=True)  # opcional, para login o contacto
    google_id = models.CharField(max_length=50, unique=True, default=0)  # si lo sincronizas con Classroom

    def __str__(self):
        return self.nombre_completo

class MateriaProfesor(models.Model):
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("profesor", "materia")  # evita duplicados

    def __str__(self):
        return f"{self.profesor} - {self.materia}"
