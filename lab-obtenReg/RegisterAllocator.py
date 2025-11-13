import collections

class RegisterAllocator:
    """
    Gestiona la asignación de registros MIPS y el desbordamiento a la pila (spilling).
    
    Este asignador utiliza un enfoque simple para la gestión de registros.
    Asigna registros temporales ($t0-$t9) primero. Si todos están ocupados,
    realiza un desbordamiento (spill) de un registro a la pila para liberar espacio.
    
    Atributos:
        temp_regs (collections.deque): Cola de registros temporales ($t) disponibles.
        saved_regs (collections.deque): Cola de registros guardados ($s) disponibles.
        register_descriptor (dict): Mapa de registro a la variable que contiene.
                                    Ej: {'$t0': 'var_x'}
        address_descriptor (dict): Mapa de una variable a su ubicación (registro o pila).
                                   Ej: {'var_x': '$t0', 'var_y': -4}
        stack_offset (int): El desplazamiento actual en la pila para el próximo desbordamiento.
        spill_code (list): Almacena el código MIPS generado para operaciones de spill/load.
    """

    def __init__(self):
        """Inicializa el asignador de registros."""
        # Inicializa los registros temporales $t0 a $t9
        self.temp_regs = collections.deque(f'$t{i}' for i in range(10))
        # Inicializa los registros guardados $s0 a $s7
        self.saved_regs = collections.deque(f'$s{i}' for i in range(8))
        
        self.register_descriptor = {}
        self.address_descriptor = {}
        
        self.stack_offset = 0
        self.spill_code = []

    def get_reg(self, var_name):
        """
        Obtiene un registro para una variable.

        Si la variable ya está en un registro, lo devuelve.
        Si hay registros temporales libres, asigna uno nuevo.
        Si no hay registros libres, realiza un desbordamiento a la pila.

        Args:
            var_name (str): El nombre de la variable para la cual se necesita un registro.

        Returns:
            str: El nombre del registro asignado (ej. '$t0').
        """
        # Caso 1: La variable ya está en un registro.
        if var_name in self.address_descriptor and isinstance(self.address_descriptor[var_name], str):
            return self.address_descriptor[var_name]

        # Caso 2: Hay registros temporales disponibles.
        if self.temp_regs:
            reg = self.temp_regs.popleft()
            self._assign_reg(reg, var_name)
            return reg

        # Caso 3: No hay registros temporales, se necesita desbordamiento (spill).
        return self._spill_register(var_name)

    def free_reg(self, reg):
        """
        Libera un registro que ya no está en uso.

        Args:
            reg (str): El registro a liberar.
        
        Returns:
            bool: True si el registro fue liberado, False en caso contrario.
        """
        if reg not in self.register_descriptor:
            return False # El registro ya estaba libre

        var_name = self.register_descriptor.pop(reg)
        if var_name in self.address_descriptor:
            # Solo se elimina si la ubicación era este registro.
            # Podría haber sido movido a la pila.
            if self.address_descriptor[var_name] == reg:
                del self.address_descriptor[var_name]

        # Devolver el registro a la cola de disponibles apropiada
        if reg.startswith('$t'):
            self.temp_regs.append(reg)
        elif reg.startswith('$s'):
            self.saved_regs.append(reg)
            
        return True

    def _assign_reg(self, reg, var_name):
        """Asigna un registro a una variable y actualiza los descriptores."""
        self.register_descriptor[reg] = var_name
        self.address_descriptor[var_name] = reg

    def _spill_register(self, new_var_name):
        """
        Realiza un desbordamiento de un registro a la pila para hacer espacio.
        
        La estrategia simple es tomar el primer registro ocupado de la lista de $t.
        Guarda su valor en la pila y lo reasigna a la nueva variable.
        """
        # Seleccionar un registro para desbordar (estrategia simple: el primero en uso)
        reg_to_spill = next(iter(self.register_descriptor))
        var_to_spill = self.register_descriptor[reg_to_spill]

        # Asignar una nueva ubicación en la pila
        self.stack_offset -= 4
        stack_pos = self.stack_offset
        
        # Generar código MIPS para el desbordamiento (store word)
        self.spill_code.append(f"sw {reg_to_spill}, {stack_pos}($sp)  # Spill {var_to_spill}")
        
        # Actualizar la ubicación de la variable desbordada
        self.address_descriptor[var_to_spill] = stack_pos
        
        # El registro ahora está "libre" para la nueva variable
        self.register_descriptor.pop(reg_to_spill)
        self._assign_reg(reg_to_spill, new_var_name)
        
        return reg_to_spill

    def load_from_stack(self, var_name):
        """
        Carga una variable desde la pila a un registro.
        
        Args:
            var_name (str): La variable a cargar.

        Returns:
            str: El registro donde se cargó la variable.
        """
        if var_name not in self.address_descriptor or not isinstance(self.address_descriptor[var_name], int):
            raise ValueError(f"La variable '{var_name}' no está en la pila.")

        stack_pos = self.address_descriptor[var_name]
        reg = self.get_reg(var_name) # Obtiene un registro (puede causar otro spill)
        
        # Generar código MIPS para cargar desde la pila (load word)
        self.spill_code.append(f"lw {reg}, {stack_pos}($sp)  # Load {var_name}")
        
        # Actualizar descriptores
        self.address_descriptor[var_name] = reg
        self.register_descriptor[reg] = var_name
        
        return reg

    def get_spill_code(self):
        """Devuelve el código de desbordamiento y limpia la lista."""
        code = self.spill_code
        self.spill_code = []
        return code