document.addEventListener('DOMContentLoaded', function() {
    const contentTypeSelect = document.getElementById('id_content_type');
    const objectIdSelect = document.getElementById('id_object_id');

    contentTypeSelect.addEventListener('change', function() {
        const contentTypeId = contentTypeSelect.value;

        fetch(`/your-url-to-get-objects?content_type=${contentTypeId}`)
            .then(response => response.json())
            .then(data => {
                objectIdSelect.innerHTML = ''; // Очистить предыдущие варианты
                data.forEach(obj => {
                    const option = new Option(obj.title, obj.id);
                    objectIdSelect.add(option);
                });
            });
    });
});