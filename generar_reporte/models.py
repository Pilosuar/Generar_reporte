from django.db import models

class Alumno(models.Model):
    # id implicito pero se agrega
    nombre_completo = models.CharField(max_length=200)
    materia = models.CharField(max_length=200)
    
class Materia(models.Model):
    # id implicito pero se agrega
    nombre = models.CharField(max_length=200)
    
# # # # # # # # T A B L A S   F O R A N E A S # # # # # # # # 
class AlumnoMateria(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    calificacion = models.IntegerField()
    
class MateriaActividad(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)  
    actividad_entregada = models.BooleanField()
    nombre_materias_no_entregadas = models.CharField(max_length=200)