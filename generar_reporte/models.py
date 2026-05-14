from django.db import models

class Alumno(models.Model):
    nombre_completo = models.CharField(max_length=200)
    google_id = models.CharField(max_length=100, unique=True)  # identificador único

    def __str__(self):
        return self.nombre_completo

class Materia(models.Model):
    nombre = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nombre

class AlumnoMateria(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    calificacion = models.IntegerField()

    class Meta:
        unique_together = ("alumno", "materia")  # evita duplicados

class MateriaActividad(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)  
    actividad_entregada = models.BooleanField()
    nombre_materias_no_entregadas = models.CharField(max_length=200)

    class Meta:
        unique_together = ("materia", "nombre_materias_no_entregadas")  # evita duplicados
