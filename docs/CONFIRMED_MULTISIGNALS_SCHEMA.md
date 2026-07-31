# Esquema del historial de multiseñales confirmadas

Archivo de datos:

runtime/confirmed_multisignals.json

## Registro natural

Un registro generado normalmente utiliza el campo:

- `warning_seconds`: segundos de propagación almacenados durante el evento.

Un registro natural no incluye campos de reconstrucción.

## Registro reconstruido

Cuando un valor de propagación se complete posteriormente, deben utilizarse siempre exactamente estas claves:

- `warning_seconds`: valor reconstruido, expresado en segundos.
- `warning_seconds_reconstructed`: valor booleano `true`.
- `warning_seconds_source`: origen utilizado para reconstruir el valor.
- `warning_seconds_reconstructed_at`: fecha y hora ISO 8601 de la reconstrucción.

Para reconstrucciones realizadas desde el inventario de la autocelda, el valor de `warning_seconds_source` es:

`reconstructed_from_cell_inventory`

## Regla de estabilidad

No deben inventarse nombres alternativos para representar segundos reconstruidos.

No utilizar variantes como:

- `reconstructed_warning_seconds`
- `warning_recovered`
- `estimated_afterwards`
- `was_rebuilt`

Toda reconstrucción futura debe reutilizar las claves definidas en este documento.
