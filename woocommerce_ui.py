import asyncio
import logging
from typing import Dict, List, Optional
import requests
import json
from datetime import datetime
import urllib3
import os
import base64
import yaml

# Importaciones para la interfaz mejorada
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
import questionary
from questionary import Style

class WooCommerceAgent:
    """Clase base para interactuar con la API de WooCommerce."""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        self.site_url = site_url.rstrip('/')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.base_url = f"{self.site_url}/wp-json/wc/v3"
        
    def _get_auth_params(self):
        """Get authentication parameters for API requests."""
        return {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
        }
        
    async def get_products(self, per_page: int = 10) -> List[Dict]:
        """Obtener lista de productos."""
        try:
            params = self._get_auth_params()
            params['per_page'] = per_page
            response = requests.get(
                f"{self.base_url}/products",
                params=params,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener productos: {str(e)}")
            return []
    
    async def get_categories(self, per_page: int = 10) -> List[Dict]:
        """Obtener lista de categorías."""
        try:
            params = self._get_auth_params()
            params['per_page'] = per_page
            response = requests.get(
                f"{self.base_url}/products/categories",
                params=params,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener categorías: {str(e)}")
            return []
    
    async def create_product(self, **kwargs) -> Optional[Dict]:
        """Crear un nuevo producto."""
        try:
            # Asegurar que los datos estén en el formato correcto
            data = {
                'name': kwargs.get('name'),
                'type': 'simple',  # Tipo de producto por defecto
                'regular_price': str(kwargs.get('price')),  # Convertir precio a string
                'description': kwargs.get('description', ''),
                'short_description': '',  # Campo requerido por WooCommerce
                'categories': [{'id': cat_id} for cat_id in kwargs.get('categories', [])],
                'images': [],  # Inicializar array de imágenes
                'status': 'publish'
            }

            # Agregar stock solo si se proporciona
            if 'stock_quantity' in kwargs:
                data.update({
                    'manage_stock': True,
                    'stock_quantity': int(kwargs['stock_quantity']),
                    'stock_status': 'instock' if int(kwargs['stock_quantity']) > 0 else 'outofstock'
                })

            # Agregar SKU si se proporciona
            if kwargs.get('sku'):
                data['sku'] = kwargs['sku']

            # Procesar imágenes si se proporcionan
            if kwargs.get('images'):
                image_data = []
                for image_path in kwargs['images']:
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as img_file:
                            image_data.append({
                                'src': image_path,
                                'name': os.path.basename(image_path)
                            })
                data['images'] = image_data

            response = requests.post(
                f"{self.base_url}/products",
                params=self._get_auth_params(),
                json=data,
                verify=False
            )
            
            # Imprimir información de depuración
            logging.debug(f"Request URL: {response.url}")
            logging.debug(f"Request Data: {data}")
            logging.debug(f"Response Status: {response.status_code}")
            logging.debug(f"Response Content: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al crear producto: {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"Respuesta del servidor: {e.response.text}")
            return None
    
    async def update_product(self, product_id: int, data: Dict) -> Optional[Dict]:
        """Actualizar un producto existente."""
        try:
            response = requests.put(
                f"{self.base_url}/products/{product_id}",
                params=self._get_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al actualizar producto: {str(e)}")
            return None
    
    async def delete_product(self, product_id: int) -> bool:
        """Eliminar un producto."""
        try:
            params = self._get_auth_params()
            params['force'] = True
            response = requests.delete(
                f"{self.base_url}/products/{product_id}",
                params=params,
                verify=False
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al eliminar producto: {str(e)}")
            return False
    
    async def create_category(self, **kwargs) -> Optional[Dict]:
        """Crear una nueva categoría."""
        try:
            response = requests.post(
                f"{self.base_url}/products/categories",
                params=self._get_auth_params(),
                json=kwargs,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al crear categoría: {str(e)}")
            return None
    
    async def update_category(self, category_id: int, data: Dict) -> Optional[Dict]:
        """Actualizar una categoría existente."""
        try:
            response = requests.put(
                f"{self.base_url}/products/categories/{category_id}",
                params=self._get_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al actualizar categoría: {str(e)}")
            return None
    
    async def delete_category(self, category_id: int) -> bool:
        """Eliminar una categoría."""
        try:
            params = self._get_auth_params()
            params['force'] = True
            response = requests.delete(
                f"{self.base_url}/products/categories/{category_id}",
                params=params,
                verify=False
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al eliminar categoría: {str(e)}")
            return False

    async def update_product_images(self, product_id: int, image_paths: List[str]) -> Optional[Dict]:
        """Actualizar las imágenes de un producto existente."""
        try:
            # Cargar credenciales de WordPress
            with open('woocommerce_config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                wp_username = config.get('username')
                wp_password = config.get('password')

            if not wp_username or not wp_password:
                logging.error("No se encontraron las credenciales de WordPress en el archivo de configuración")
                return None

            # Crear credenciales en base64 para autenticación básica
            import base64
            credentials = base64.b64encode(f"{wp_username}:{wp_password}".encode()).decode()

            # Primero, subir las imágenes a WordPress
            images = []
            for image_path in image_paths:
                if not os.path.exists(image_path):
                    logging.error(f"La imagen no existe: {image_path}")
                    continue

                # Obtener el nombre del archivo y normalizarlo
                import unicodedata
                filename = os.path.basename(image_path)
                safe_filename = unicodedata.normalize('NFKD', filename)\
                    .encode('ASCII', 'ignore')\
                    .decode('ASCII')\
                    .replace(' ', '-')

                # Leer el archivo de imagen
                with open(image_path, 'rb') as img_file:
                    files = {
                        'file': (safe_filename, img_file, 'image/jpeg')
                    }
                    
                    # Subir la imagen a WordPress Media Library usando autenticación básica
                    media_response = requests.post(
                        f"{self.site_url}/wp-json/wp/v2/media",
                        headers={
                            'Authorization': f'Basic {credentials}',
                            'Content-Disposition': f'attachment; filename="{safe_filename}"'
                        },
                        files=files,
                        verify=False
                    )
                    
                    if media_response.status_code == 201:
                        media_data = media_response.json()
                        images.append({
                            'src': media_data['source_url'],
                            'name': safe_filename,
                            'alt': os.path.splitext(safe_filename)[0]
                        })
                        self.logger.info(f"Imagen subida exitosamente: {safe_filename}")
                    else:
                        logging.error(f"Error al subir imagen: {media_response.text}")
                        logging.error(f"Código de estado: {media_response.status_code}")

            if not images:
                logging.error("No se pudo subir ninguna imagen")
                return None

            # Actualizar el producto con las nuevas imágenes usando las credenciales de WooCommerce
            data = {'images': images}
            response = requests.put(
                f"{self.base_url}/products/{product_id}",
                params=self._get_auth_params(),
                json=data,
                verify=False
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error actualizando imágenes del producto: {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"Respuesta del servidor: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"Error inesperado: {str(e)}")
            return None

class WooCommerceUI:
    """Interfaz de usuario moderna para el agente de WooCommerce."""
    
    # Estilo personalizado para los menús interactivos
    custom_style = Style([
        ('qmark', '#ff5f00 bold'),        # Símbolo de pregunta
        ('question', '#00afff bold'),     # Texto de la pregunta
        ('answer', '#00ff5f bold'),       # Respuesta seleccionada
        ('pointer', '#ff5f00 bold'),      # Puntero de selección
        ('selected', '#00ff5f bold'),     # Opción seleccionada
        ('instruction', '#808080 italic'), # Instrucciones adicionales
    ])
    
    def __init__(self, agent: WooCommerceAgent):
        self.agent = agent
        self.console = Console()
    
    async def main_menu(self):
        """Menú principal interactivo con selección por flechas."""
        while True:
            self.console.clear()
            self.console.print("[bold blue]╔══════════════════════════════════════╗[/bold blue]", justify="center")
            self.console.print("[bold blue]║       WooCommerce Manager            ║[/bold blue]", justify="center")
            self.console.print("[bold blue]╚══════════════════════════════════════╝[/bold blue]", justify="center")
            
            choice = await questionary.select(
                "¿Qué deseas hacer?",
                choices=[
                    "💼 Gestionar Productos",
                    "📁 Gestionar Categorías",
                    "⚙️ Configuración",
                    "🚪 Salir"
                ],
                style=self.custom_style
            ).ask_async()
            
            if "Productos" in choice:
                await self.product_menu()
            elif "Categorías" in choice:
                await self.category_menu()
            elif "Configuración" in choice:
                await self.config_menu()
            else:
                self.console.print(Panel("[yellow]Saliendo del programa...[/yellow]", 
                                        title="Adiós", border_style="yellow"))
                break

    async def product_menu(self):
        """Submenú para gestión de productos."""
        while True:
            self.console.clear()
            self.console.print("[bold green]Gestión de Productos[/bold green]", justify="center")
            self.console.print("=" * 50, justify="center")
            
            choice = await questionary.select(
                "Selecciona una opción:",
                choices=[
                    "📋 Listar Productos",
                    "🔍 Ver Detalles de Producto",
                    "➕ Crear Nuevo Producto",
                    "✏️ Actualizar Producto",
                    "🗑️ Eliminar Producto",
                    "🖼️ Gestionar Imágenes",
                    "⬅️ Volver al Menú Principal"
                ],
                style=self.custom_style
            ).ask_async()
            
            if "Listar" in choice:
                await self.list_products()
            elif "Detalles" in choice:
                await self.view_product_details()
            elif "Crear" in choice:
                await self.create_product_form()
            elif "Actualizar" in choice:
                await self.update_product_form()
            elif "Eliminar" in choice:
                await self.delete_product_form()
            elif "Imágenes" in choice:
                await self.manage_product_images()
            elif "Volver" in choice:
                break

    async def list_products(self):
        """Muestra una tabla formateada con los productos."""
        self.console.clear()
        
        # Mostrar spinner mientras se cargan los datos
        with self.console.status("[bold green]Cargando productos...", spinner="dots"):
            products = await self.agent.get_products(per_page=20)
        
        if not products:
            self.console.print(Panel("[yellow]No se encontraron productos[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear una tabla con Rich
        table = Table(title="Productos en la Tienda")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Nombre", style="green")
        table.add_column("Precio", style="yellow", justify="right")
        table.add_column("Stock", style="magenta", justify="right")
        table.add_column("SKU", style="blue")
        table.add_column("Imágenes", style="red", justify="center")
        
        # Llenar la tabla con datos
        for p in products:
            table.add_row(
                str(p['id']),
                p['name'],
                f"${p.get('price', '0.00')}",
                str(p.get('stock_quantity', 'N/A')),
                p.get('sku', 'N/A'),
                str(len(p.get('images', [])))
            )
        
        # Mostrar la tabla
        self.console.print(table)
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def category_menu(self):
        """Submenú para gestión de categorías."""
        while True:
            self.console.clear()
            self.console.print("[bold cyan]Gestión de Categorías[/bold cyan]", justify="center")
            self.console.print("=" * 50, justify="center")
            
            choice = await questionary.select(
                "Selecciona una opción:",
                choices=[
                    "📋 Listar Categorías",
                    "➕ Crear Nueva Categoría",
                    "✏️ Actualizar Categoría",
                    "🗑️ Eliminar Categoría",
                    "⬅️ Volver al Menú Principal"
                ],
                style=self.custom_style
            ).ask_async()
            
            if "Listar" in choice:
                await self.list_categories()
            elif "Crear" in choice:
                await self.create_category_form()
            elif "Actualizar" in choice:
                await self.update_category_form()
            elif "Eliminar" in choice:
                await self.delete_category_form()
            elif "Volver" in choice:
                break

    async def config_menu(self):
        """Menú de configuración."""
        self.console.clear()
        self.console.print("[bold magenta]Configuración[/bold magenta]", justify="center")
        self.console.print("=" * 50, justify="center")
        
        choice = await questionary.select(
            "Opciones de configuración:",
            choices=[
                "🔑 Cambiar Credenciales API",
                "💾 Exportar Productos a CSV",
                "⬅️ Volver al Menú Principal"
            ],
            style=self.custom_style
        ).ask_async()
        
        if "Credenciales" in choice:
            await self.update_credentials()
        elif "Exportar" in choice:
            await self.export_products()

    async def view_product_details(self):
        """Ver detalles completos de un producto específico."""
        self.console.clear()
        
        # Primero listar productos resumidos para seleccionar
        with self.console.status("[bold green]Cargando productos...", spinner="dots"):
            products = await self.agent.get_products(per_page=20)
        
        if not products:
            self.console.print(Panel("[yellow]No se encontraron productos[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear opciones para el selector
        choices = [
            f"{p['id']} - {p['name']} (${p.get('price', '0.00')})"
            for p in products
        ]
        choices.append("⬅️ Cancelar")
        
        # Mostrar selector
        selected = await questionary.select(
            "Selecciona un producto para ver detalles:",
            choices=choices,
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in selected:
            return
        
        # Extraer ID del producto seleccionado
        product_id = int(selected.split(" - ")[0])
        
        # Buscar el producto en la lista
        product = None
        for p in products:
            if p['id'] == product_id:
                product = p
                break
        
        if not product:
            self.console.print("[bold red]Error: Producto no encontrado[/bold red]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Mostrar detalles completos del producto
        self.console.clear()
        self.console.print(f"[bold green]Detalles del Producto: {product['name']}[/bold green]", justify="center")
        self.console.print("=" * 70, justify="center")
        
        # Panel con información básica
        basic_info = f"""[cyan]ID:[/cyan] {product['id']}
[cyan]Nombre:[/cyan] {product['name']}
[cyan]Precio:[/cyan] ${product.get('price', '0.00')}
[cyan]SKU:[/cyan] {product.get('sku', 'N/A')}
[cyan]Stock:[/cyan] {product.get('stock_quantity', 'N/A')}
[cyan]Estado:[/cyan] {product.get('status', 'N/A')}
[cyan]Fecha creación:[/cyan] {product.get('date_created', 'N/A')}
[cyan]Categorías:[/cyan] {', '.join([c.get('name', '') for c in product.get('categories', [])])}
"""
        
        self.console.print(Panel(basic_info, title="Información Básica", border_style="green"))
        
        # Panel con descripción
        if product.get('description'):
            self.console.print(Panel(
                product['description'], 
                title="Descripción", 
                border_style="yellow"
            ))
        
        # Mostrar imágenes si hay
        if product.get('images'):
            image_list = "\n".join([f"[link={img.get('src', '')}]{img.get('name', 'Imagen')}: {img.get('src', '')}[/link]" 
                                 for img in product.get('images', [])])
            self.console.print(Panel(image_list, title=f"Imágenes ({len(product.get('images', []))})", border_style="blue"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def create_product_form(self):
        """Formulario interactivo para crear un producto."""
        self.console.clear()
        self.console.print("[bold green]Crear Nuevo Producto[/bold green]", justify="center")
        self.console.print("=" * 50, justify="center")
        
        # Obtener datos con validación
        name = await questionary.text(
            "Nombre del producto:",
            validate=lambda text: True if len(text) > 0 else "El nombre no puede estar vacío"
        ).ask_async()
        
        description = await questionary.text(
            "Descripción (puedes usar HTML):"
        ).ask_async()
        
        price = await questionary.text(
            "Precio:",
            validate=lambda text: True if text.replace('.', '', 1).isdigit() else "Ingresa un número válido"
        ).ask_async()
        
        stock = await questionary.text(
            "Cantidad en stock:",
            validate=lambda text: True if text.isdigit() else "Ingresa un número entero"
        ).ask_async()
        
        # Generar SKU automáticamente
        import random
        import string
        from datetime import datetime
        
        # Formato: YYYYMMDD-XXXX donde X son letras/números aleatorios
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        sku = f"{date_part}-{random_part}"
        
        # Selección de categorías
        with self.console.status("[bold cyan]Cargando categorías...", spinner="dots"):
            categories = await self.agent.get_categories()
        
        if not categories:
            self.console.print(Panel("[yellow]No se encontraron categorías disponibles[/yellow]", 
                                    title="Información", border_style="yellow"))
            selected_categories = []
        else:
            # Crear opciones para el selector
            category_choices = [
                questionary.Choice(title=f"{c['name']} (ID: {c['id']})", value=c['id'])
                for c in categories
            ]
            category_choices.append(questionary.Choice(title="✅ Finalizar selección", value='finish'))
            
            selected_categories = []
            self.console.print("\n[bold cyan]Selecciona las categorías para el producto:[/bold cyan]")
            self.console.print("[dim](Puedes seleccionar múltiples categorías, selecciona 'Finalizar selección' cuando termines)[/dim]\n")
            
            while True:
                if selected_categories:
                    self.console.print("\n[green]Categorías seleccionadas:[/green]")
                    for cat_id in selected_categories:
                        cat_name = next((c['name'] for c in categories if c['id'] == cat_id), "Desconocida")
                        self.console.print(f"  ✓ {cat_name} (ID: {cat_id})")
                
                choice = await questionary.select(
                    "\nSelecciona una categoría:",
                    choices=[c for c in category_choices if c.value == 'finish' or c.value not in selected_categories],
                    style=self.custom_style
                ).ask_async()
                
                if choice == 'finish':
                    break
                
                selected_categories.append(choice)
            
            self.console.print(f"\n[bold green]✓ {len(selected_categories)} categorías seleccionadas[/bold green]")
        
        # Manejo de imágenes
        images = []
        add_image = await questionary.confirm("¿Deseas agregar imágenes?").ask_async()
        
        while add_image:
            image_path = await questionary.text(
                "Ruta de la imagen:",
                validate=lambda text: True if os.path.exists(text) else "El archivo no existe"
            ).ask_async()
            
            images.append(image_path)
            add_image = await questionary.confirm("¿Agregar otra imagen?").ask_async()
        
        # Confirmación final
        self.console.print("\n[bold]Resumen del producto a crear:[/bold]")
        self.console.print(f"Nombre: [green]{name}[/green]")
        self.console.print(f"Precio: [yellow]${price}[/yellow]")
        self.console.print(f"Stock: [magenta]{stock}[/magenta]")
        self.console.print(f"SKU: [blue]{sku}[/blue]")
        self.console.print(f"Categorías: [cyan]{len(selected_categories)}[/cyan]")
        self.console.print(f"Imágenes: [red]{len(images)}[/red]")
        
        confirm = await questionary.confirm("¿Confirmas la creación del producto?").ask_async()
        if not confirm:
            self.console.print("[yellow]Operación cancelada[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear producto con barra de progreso
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Creando producto..."),
            console=self.console
        ) as progress:
            product = await self.agent.create_product(
                name=name,
                description=description,
                price=float(price),
                categories=selected_categories,
                images=images,
                stock_quantity=int(stock),
                sku=sku
            )
        
        if product:
            self.console.print(Panel("[bold green]¡Producto creado exitosamente![/bold green]", 
                                    title=f"Producto #{product['id']}", border_style="green"))
        else:
            self.console.print(Panel("[bold red]Error al crear el producto[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def update_product_form(self):
        """Formulario para actualizar un producto existente."""
        self.console.clear()
        
        # Primero listar productos resumidos para seleccionar
        with self.console.status("[bold green]Cargando productos...", spinner="dots"):
            products = await self.agent.get_products(per_page=20)
        
        if not products:
            self.console.print(Panel("[yellow]No se encontraron productos[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear opciones para el selector
        choices = [
            f"{p['id']} - {p['name']} (${p.get('price', '0.00')})"
            for p in products
        ]
        choices.append("⬅️ Cancelar")
        
        # Mostrar selector
        selected = await questionary.select(
            "Selecciona un producto para actualizar:",
            choices=choices,
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in selected:
            return
        
        # Extraer ID del producto seleccionado
        product_id = int(selected.split(" - ")[0])
        
        # Buscar el producto en la lista
        product = None
        for p in products:
            if p['id'] == product_id:
                product = p
                break
        
        if not product:
            self.console.print("[bold red]Error: Producto no encontrado[/bold red]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Formulario de actualización
        self.console.clear()
        self.console.print(f"[bold green]Actualizar Producto: {product['name']}[/bold green]", justify="center")
        self.console.print("=" * 60, justify="center")
        self.console.print("[yellow]Deja en blanco los campos que no quieras actualizar[/yellow]")
        
        data = {}
        
        # Nombre
        name = await questionary.text(
            f"Nuevo nombre (actual: {product['name']}):"
        ).ask_async()
        if name:
            data['name'] = name
        
        # Descripción (mostrar primeros caracteres)
        current_desc = product.get('description', '')[:50] + ('...' if len(product.get('description', '')) > 50 else '')
        description = await questionary.text(
            f"Nueva descripción (actual: {current_desc}):"
        ).ask_async()
        if description:
            data['description'] = description
        
        # Precio
        price = await questionary.text(
            f"Nuevo precio (actual: ${product.get('price', '0.00')}):",
            validate=lambda text: True if not text or text.replace('.', '', 1).isdigit() else "Ingresa un número válido"
        ).ask_async()
        if price:
            data['regular_price'] = str(float(price))
        
        # Stock
        stock = await questionary.text(
            f"Nueva cantidad en stock (actual: {product.get('stock_quantity', 'N/A')}):",
            validate=lambda text: True if not text or text.isdigit() else "Ingresa un número entero"
        ).ask_async()
        if stock:
            data['manage_stock'] = True
            data['stock_quantity'] = int(stock)
        
        # SKU
        sku = await questionary.text(
            f"Nuevo SKU (actual: {product.get('sku', 'N/A')}):"
        ).ask_async()
        if sku:
            data['sku'] = sku
        
        if not data:
            self.console.print("[yellow]No se especificaron cambios para realizar[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Confirmación
        confirm = await questionary.confirm("¿Confirmas la actualización del producto?").ask_async()
        if not confirm:
            self.console.print("[yellow]Operación cancelada[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Actualizar producto
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Actualizando producto..."),
            console=self.console
        ) as progress:
            updated_product = await self.agent.update_product(product_id, data)
        
        if updated_product:
            self.console.print(Panel("[bold green]¡Producto actualizado exitosamente![/bold green]", 
                                    title=f"Producto #{product_id}", border_style="green"))
        else:
            self.console.print(Panel("[bold red]Error al actualizar el producto[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def delete_product_form(self):
        """Formulario para eliminar un producto."""
        self.console.clear()
        
        # Primero listar productos resumidos para seleccionar
        with self.console.status("[bold green]Cargando productos...", spinner="dots"):
            products = await self.agent.get_products(per_page=20)
        
        if not products:
            self.console.print(Panel("[yellow]No se encontraron productos[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear opciones para el selector
        choices = [
            f"{p['id']} - {p['name']} (${p.get('price', '0.00')})"
            for p in products
        ]
        choices.append("⬅️ Cancelar")
        
        # Mostrar selector
        selected = await questionary.select(
            "Selecciona un producto para eliminar:",
            choices=choices,
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in selected:
            return
        
        # Extraer ID y nombre del producto seleccionado
        parts = selected.split(" - ")
        product_id = int(parts[0])
        product_name = parts[1].split(" (")[0]
        
        # Confirmación con advertencia
        self.console.print(f"[bold red]⚠️ ADVERTENCIA: Vas a eliminar permanentemente el producto:[/bold red]")
        self.console.print(f"[bold yellow]ID: {product_id} - {product_name}[/bold yellow]")
        
        # Doble confirmación para operaciones destructivas
        confirm1 = await questionary.confirm("¿Estás seguro de que deseas eliminar este producto?").ask_async()
        if not confirm1:
            self.console.print("[yellow]Operación cancelada[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        confirm2 = await questionary.text(
            f'Escribe "ELIMINAR" para confirmar la eliminación de "{product_name}":',
            validate=lambda text: True if text == "ELIMINAR" else "Debes escribir ELIMINAR para confirmar"
        ).ask_async()
        
        # Eliminar producto
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold red]Eliminando producto..."),
            console=self.console
        ) as progress:
            success = await self.agent.delete_product(product_id)
        
        if success:
            self.console.print(Panel("[bold green]¡Producto eliminado exitosamente![/bold green]", 
                                    title="Operación Completada", border_style="green"))
        else:
            self.console.print(Panel("[bold red]Error al eliminar el producto[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def manage_product_images(self):
        """Gestionar imágenes de un producto específico."""
        self.console.clear()
        
        # Primero listar productos resumidos para seleccionar
        with self.console.status("[bold green]Cargando productos...", spinner="dots"):
            products = await self.agent.get_products(per_page=20)
        
        if not products:
            self.console.print(Panel("[yellow]No se encontraron productos[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear opciones para el selector
        choices = [
            f"{p['id']} - {p['name']} ({len(p.get('images', []))} imágenes)"
            for p in products
        ]
        choices.append("⬅️ Cancelar")
        
        # Mostrar selector
        selected = await questionary.select(
            "Selecciona un producto para gestionar sus imágenes:",
            choices=choices,
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in selected:
            return
        
        # Extraer ID del producto seleccionado
        product_id = int(selected.split(" - ")[0])
        
        # Opciones de gestión de imágenes
        action = await questionary.select(
            "¿Qué acción deseas realizar?",
            choices=[
                "➕ Agregar nuevas imágenes",
                "🔄 Reemplazar todas las imágenes",
                "⬅️ Cancelar"
            ],
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in action:
            return
        
        # Recopilar nuevas imágenes
        images = []
        while True:
            image_path = await questionary.text(
                "Ruta de la imagen (deja vacío para terminar):",
                validate=lambda text: True if not text or os.path.exists(text) else "El archivo no existe"
            ).ask_async()
            
            if not image_path:
                break
                
            images.append(image_path)
            
            if len(images) > 0:
                self.console.print(f"[green]✓ Imagen agregada: {image_path}[/green]")
        
        if not images:
            self.console.print("[yellow]No se especificaron imágenes para agregar[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Actualizar imágenes
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Procesando imágenes..."),
            console=self.console
        ) as progress:
            product = await self.agent.update_product_images(product_id, images)
        
        if product:
            self.console.print(Panel(
                f"[bold green]Imágenes actualizadas correctamente[/bold green]\n" +
                f"Total de imágenes: {len(product.get('images', []))}",
                title="Operación Completada", 
                border_style="green"
            ))
        else:
            self.console.print(Panel("[bold red]Error al actualizar las imágenes[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def list_categories(self):
        """Muestra una tabla formateada con las categorías."""
        self.console.clear()
        
        with self.console.status("[bold cyan]Cargando categorías...", spinner="dots"):
            categories = await self.agent.get_categories(per_page=50)
        
        if not categories:
            self.console.print(Panel("[yellow]No se encontraron categorías[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        table = Table(title="Categorías en la Tienda")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Nombre", style="green")
        table.add_column("Descripción", style="yellow")
        table.add_column("Productos", style="magenta", justify="right")
        table.add_column("Parent", style="blue")
        
        for c in categories:
            parent_name = "Ninguno"
            if c.get('parent', 0) > 0:
                for parent in categories:
                    if parent['id'] == c['parent']:
                        parent_name = parent['name']
                        break
            
            table.add_row(
                str(c['id']),
                c['name'],
                c.get('description', '')[:50] + ('...' if len(c.get('description', '')) > 50 else ''),
                str(c.get('count', 0)),
                parent_name
            )
        
        self.console.print(table)
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def create_category_form(self):
        """Formulario para crear una nueva categoría."""
        self.console.clear()
        self.console.print("[bold cyan]Crear Nueva Categoría[/bold cyan]", justify="center")
        self.console.print("=" * 50, justify="center")
        
        # Obtener datos
        name = await questionary.text(
            "Nombre de la categoría:",
            validate=lambda text: True if len(text) > 0 else "El nombre no puede estar vacío"
        ).ask_async()
        
        description = await questionary.text(
            "Descripción (opcional):"
        ).ask_async()
        
        # Selección de categoría padre
        with self.console.status("[bold cyan]Cargando categorías...", spinner="dots"):
            categories = await self.agent.get_categories()
        
        self.console.print("\n[bold]Categorías disponibles como padre:[/bold]")
        
        # Crear opciones para el selector
        parent_choices = [
            questionary.Choice(title="Ninguna (categoría principal)", value=0)
        ]
        
        for c in categories:
            parent_choices.append(
                questionary.Choice(title=f"{c['name']} (ID: {c['id']})", value=c['id'])
            )
        
        parent_id = await questionary.select(
            "Selecciona la categoría padre:",
            choices=parent_choices,
            style=self.custom_style
        ).ask_async()
        
        # Confirmación
        self.console.print("\n[bold]Resumen de la categoría a crear:[/bold]")
        self.console.print(f"Nombre: [cyan]{name}[/cyan]")
        self.console.print(f"Descripción: [yellow]{description or 'N/A'}[/yellow]")
        self.console.print(f"Categoría padre: [magenta]{parent_id if parent_id > 0 else 'Ninguna'}[/magenta]")
        
        confirm = await questionary.confirm("¿Confirmas la creación de la categoría?").ask_async()
        if not confirm:
            self.console.print("[yellow]Operación cancelada[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear categoría
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Creando categoría..."),
            console=self.console
        ) as progress:
            category = await self.agent.create_category(
                name=name,
                description=description,
                parent=parent_id if parent_id > 0 else None
            )
        
        if category:
            self.console.print(Panel("[bold green]¡Categoría creada exitosamente![/bold green]", 
                                    title=f"Categoría #{category['id']}", border_style="green"))
        else:
            self.console.print(Panel("[bold red]Error al crear la categoría[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def update_category_form(self):
        """Formulario para actualizar una categoría existente."""
        self.console.clear()
        
        # Primero listar categorías resumidas para seleccionar
        with self.console.status("[bold cyan]Cargando categorías...", spinner="dots"):
            categories = await self.agent.get_categories()
        
        if not categories:
            self.console.print(Panel("[yellow]No se encontraron categorías[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear opciones para el selector
        choices = [
            f"{c['id']} - {c['name']}"
            for c in categories
        ]
        choices.append("⬅️ Cancelar")
        
        # Mostrar selector
        selected = await questionary.select(
            "Selecciona una categoría para actualizar:",
            choices=choices,
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in selected:
            return
        
        # Extraer ID de la categoría seleccionada
        category_id = int(selected.split(" - ")[0])
        
        # Buscar la categoría en la lista
        category = None
        for c in categories:
            if c['id'] == category_id:
                category = c
                break
        
        if not category:
            self.console.print("[bold red]Error: Categoría no encontrada[/bold red]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Formulario de actualización
        self.console.clear()
        self.console.print(f"[bold cyan]Actualizar Categoría: {category['name']}[/bold cyan]", justify="center")
        self.console.print("=" * 60, justify="center")
        self.console.print("[yellow]Deja en blanco los campos que no quieras actualizar[/yellow]")
        
        data = {}
        
        # Nombre
        name = await questionary.text(
            f"Nuevo nombre (actual: {category['name']}):"
        ).ask_async()
        if name:
            data['name'] = name
        
        # Descripción
        current_desc = category.get('description', '')[:50] + ('...' if len(category.get('description', '')) > 50 else '')
        description = await questionary.text(
            f"Nueva descripción (actual: {current_desc}):"
        ).ask_async()
        if description:
            data['description'] = description
        
        if not data:
            self.console.print("[yellow]No se especificaron cambios para realizar[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Confirmación
        confirm = await questionary.confirm("¿Confirmas la actualización de la categoría?").ask_async()
        if not confirm:
            self.console.print("[yellow]Operación cancelada[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Actualizar categoría
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Actualizando categoría..."),
            console=self.console
        ) as progress:
            updated_category = await self.agent.update_category(category_id, data)
        
        if updated_category:
            self.console.print(Panel("[bold green]¡Categoría actualizada exitosamente![/bold green]", 
                                    title=f"Categoría #{category_id}", border_style="green"))
        else:
            self.console.print(Panel("[bold red]Error al actualizar la categoría[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def delete_category_form(self):
        """Formulario para eliminar una categoría."""
        self.console.clear()
        
        # Primero listar categorías resumidas para seleccionar
        with self.console.status("[bold cyan]Cargando categorías...", spinner="dots"):
            categories = await self.agent.get_categories()
        
        if not categories:
            self.console.print(Panel("[yellow]No se encontraron categorías[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Crear opciones para el selector
        choices = [
            f"{c['id']} - {c['name']} ({c.get('count', 0)} productos)"
            for c in categories
        ]
        choices.append("⬅️ Cancelar")
        
        # Mostrar selector
        selected = await questionary.select(
            "Selecciona una categoría para eliminar:",
            choices=choices,
            style=self.custom_style
        ).ask_async()
        
        if "Cancelar" in selected:
            return
        
        # Extraer ID y nombre de la categoría seleccionada
        parts = selected.split(" - ")
        category_id = int(parts[0])
        category_name = parts[1].split(" (")[0]
        
        # Verificar si tiene productos
        products_count = 0
        for c in categories:
            if c['id'] == category_id:
                products_count = c.get('count', 0)
                break
        
        # Mostrar advertencia
        self.console.print(f"[bold red]⚠️ ADVERTENCIA: Vas a eliminar permanentemente la categoría:[/bold red]")
        self.console.print(f"[bold yellow]ID: {category_id} - {category_name}[/bold yellow]")
        
        if products_count > 0:
            self.console.print(f"[bold red]⚠️ Esta categoría contiene {products_count} productos![/bold red]")
            self.console.print("[bold red]Los productos no serán eliminados, pero perderán esta categoría.[/bold red]")
        
        # Doble confirmación para operaciones destructivas
        confirm1 = await questionary.confirm("¿Estás seguro de que deseas eliminar esta categoría?").ask_async()
        if not confirm1:
            self.console.print("[yellow]Operación cancelada[/yellow]")
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        confirm2 = await questionary.text(
            f'Escribe "ELIMINAR" para confirmar la eliminación de "{category_name}":',
            validate=lambda text: True if text == "ELIMINAR" else "Debes escribir ELIMINAR para confirmar"
        ).ask_async()
        
        # Eliminar categoría
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold red]Eliminando categoría..."),
            console=self.console
        ) as progress:
            success = await self.agent.delete_category(category_id)
        
        if success:
            self.console.print(Panel("[bold green]¡Categoría eliminada exitosamente![/bold green]", 
                                    title="Operación Completada", border_style="green"))
        else:
            self.console.print(Panel("[bold red]Error al eliminar la categoría[/bold red]", 
                                    title="Error", border_style="red"))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def update_credentials(self):
        """Actualizar las credenciales de la API de WooCommerce."""
        self.console.clear()
        self.console.print("[bold magenta]Actualizar Credenciales API[/bold magenta]", justify="center")
        self.console.print("=" * 50, justify="center")
        
        self.console.print(Panel(
            "Esta opción permite cambiar las credenciales de conexión a la API de WooCommerce.\n" +
            "Las credenciales actuales serán reemplazadas por las nuevas que ingreses.",
            title="Información",
            border_style="blue"
        ))
        
        # Obtener nuevas credenciales
        site_url = await questionary.text(
            "URL del sitio (ej. https://miweb.com):",
            validate=lambda text: True if text.startswith("http") else "Debe ser una URL válida comenzando con http:// o https://"
        ).ask_async()
        
        consumer_key = await questionary.text(
            "Consumer Key:",
            validate=lambda text: True if len(text) > 0 else "No puede estar vacío"
        ).ask_async()
        
        consumer_secret = await questionary.password(
            "Consumer Secret:",
            validate=lambda text: True if len(text) > 0 else "No puede estar vacío"
        ).ask_async()
        
        # Guardar en archivo de configuración
        config = {
            'site_url': site_url,
            'consumer_key': consumer_key,
            'consumer_secret': consumer_secret
        }
        
        try:
            with open('woocommerce_config.yaml', 'w') as f:
                yaml.dump(config, f)
            
            self.console.print(Panel(
                "[bold green]¡Credenciales guardadas correctamente![/bold green]\n" +
                "Los cambios se aplicarán al reiniciar la aplicación.",
                title="Éxito",
                border_style="green"
            ))
        except Exception as e:
            self.console.print(Panel(
                f"[bold red]Error al guardar las credenciales: {str(e)}[/bold red]",
                title="Error",
                border_style="red"
            ))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

    async def export_products(self):
        """Exportar productos a un archivo CSV."""
        self.console.clear()
        self.console.print("[bold magenta]Exportar Productos[/bold magenta]", justify="center")
        self.console.print("=" * 50, justify="center")
        
        # Obtener datos
        with self.console.status("[bold green]Cargando productos...", spinner="dots"):
            products = await self.agent.get_products(per_page=100)  # Más productos para la exportación
        
        if not products:
            self.console.print(Panel("[yellow]No hay productos para exportar[/yellow]", 
                                    title="Información", border_style="yellow"))
            await questionary.text("Presiona Enter para continuar...").ask_async()
            return
        
        # Preguntar ruta del archivo
        filename = await questionary.text(
            "Nombre del archivo (por defecto: productos_export.csv):",
        ).ask_async()
        
        if not filename:
            filename = "productos_export.csv"
        
        # Crear CSV en memoria primero
        import csv
        from io import StringIO
        
        # Definir encabezados
        headers = ['ID', 'Nombre', 'SKU', 'Precio', 'Stock', 'Categorías', 'Descripción']
        
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(headers)
        
        # Añadir filas
        for p in products:
            categories = ", ".join([c.get('name', '') for c in p.get('categories', [])])
            description = p.get('description', '').replace('<p>', '').replace('</p>', ' ').replace('\n', ' ')
            
            csv_writer.writerow([
                p['id'],
                p['name'],
                p.get('sku', ''),
                p.get('price', '0.00'),
                p.get('stock_quantity', ''),
                categories,
                description[:200]  # Limitar descripción para el CSV
            ])
        
        # Guardar a archivo
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_buffer.getvalue())
            
            self.console.print(Panel(
                f"[bold green]¡{len(products)} productos exportados correctamente![/bold green]\n" +
                f"Archivo guardado como: {os.path.abspath(filename)}",
                title="Exportación Completada", 
                border_style="green"
            ))
        except Exception as e:
            self.console.print(Panel(
                f"[bold red]Error al exportar: {str(e)}[/bold red]",
                title="Error",
                border_style="red"
            ))
        
        await questionary.text("Presiona Enter para continuar...").ask_async()

async def load_config():
    """Carga la configuración desde archivo o la solicita al usuario."""
    config = {}
    config_file = 'woocommerce_config.yaml'
    
    console = Console()
    
    try:
        # Intentar cargar configuración existente
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        console.print(Panel(
            f"[green]Configuración cargada desde {config_file}[/green]",
            title="Configuración", 
            border_style="green"
        ))
    except FileNotFoundError:
        # Si no existe, crear configuración inicial
        console.print(Panel(
            "[yellow]No se encontró archivo de configuración. Se iniciará la configuración inicial.[/yellow]",
            title="Primera Ejecución", 
            border_style="yellow"
        ))
        
        # Estilo para los prompts de configuración
        custom_style = Style([
            ('qmark', '#ff5f00 bold'),
            ('question', '#00afff bold'),
            ('answer', '#00ff5f bold')
        ])
        
        site_url = await questionary.text(
            "URL del sitio WooCommerce (ej. https://miweb.com):",
            validate=lambda text: True if text.startswith("http") else "Debe ser una URL válida comenzando con http:// o https://",
            style=custom_style
        ).ask_async()
        
        consumer_key = await questionary.text(
            "Consumer Key de WooCommerce:",
            validate=lambda text: True if len(text) > 0 else "No puede estar vacío",
            style=custom_style
        ).ask_async()
        
        consumer_secret = await questionary.password(
            "Consumer Secret de WooCommerce:",
            validate=lambda text: True if len(text) > 0 else "No puede estar vacío",
            style=custom_style
        ).ask_async()
        
        config = {
            'site_url': site_url,
            'consumer_key': consumer_key,
            'consumer_secret': consumer_secret
        }
        
        # Guardar configuración
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        console.print(Panel(
            f"[green]¡Configuración guardada correctamente en {config_file}![/green]",
            title="Configuración Completada", 
            border_style="green"
        ))
    
    return config

async def main():
    """Función principal que inicia la aplicación."""
    # Configurar logging bonito con Rich
    console = Console()
    
    try:
        # Mostrar splash screen
        console.clear()
        console.print("\n\n")
        console.print("[bold blue]╔═══════════════════════════════════════════════╗[/bold blue]", justify="center")
        console.print("[bold blue]║                                               ║[/bold blue]", justify="center")
        console.print("[bold blue]║   [bold white]WooCommerce[/bold white] [bold green]Manager[/bold green]                      ║[/bold blue]", justify="center")
        console.print("[bold blue]║   [yellow]Una interfaz moderna para tu tienda online[/yellow]   ║[/bold blue]", justify="center")
        console.print("[bold blue]║                                               ║[/bold blue]", justify="center")
        console.print("[bold blue]╚═══════════════════════════════════════════════╝[/bold blue]", justify="center")
        console.print("\n")
        
        # Cargar configuración
        try:
            with open('woocommerce_config.yaml', 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            console.print(Panel(
                "[bold red]Error: No se encontró el archivo de configuración[/bold red]\n" +
                "Por favor, asegúrate de que el archivo woocommerce_config.yaml existe.",
                title="Error de Configuración",
                border_style="red"
            ))
            return
        
        # Iniciar con spinner mientras se conecta
        with console.status("[bold green]Conectando con WooCommerce API...", spinner="dots"):
            # Inicializar el agente
            agent = WooCommerceAgent(
                site_url=config['site_url'].strip(),  # Asegurarse de que no hay espacios
                consumer_key=config['consumer_key'],
                consumer_secret=config['consumer_secret']
            )
        
        console.print("[bold green]✓ Conexión establecida correctamente[/bold green]")
        
        # Iniciar la interfaz de usuario
        ui = WooCommerceUI(agent)
        await ui.main_menu()
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow][{datetime.now().strftime('%H:%M:%S')}] Interrupción recibida. Cerrando aplicación...[/yellow]")
    except requests.exceptions.RequestException as e:
        console.print(Panel(
            f"[bold red]Error de conexión con la API de WooCommerce:[/bold red]\n{str(e)}\n\n" +
            "[yellow]Verifique que las credenciales sean correctas y que el sitio esté accesible.[/yellow]",
            title="Error de Conexión", 
            border_style="red"
        ))
    except Exception as e:
        console.print(Panel(
            f"[bold red]Error inesperado:[/bold red]\n{str(e)}",
            title="Error", 
            border_style="red"
        ))
        import traceback
        console.print(traceback.format_exc(), style="dim")

if __name__ == "__main__":
    # Deshabilitar advertencias de SSL
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Ejecutar la aplicación
    asyncio.run(main()) 