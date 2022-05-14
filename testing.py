import io
import generate_ticket
import filecmp
import PIL

created_ticket = generate_ticket.generate_avia_ticket('Москва', 'Екатеринбург', '2020-12-28 в 17-25')
with open("created.png", "wb") as f:
    f.write(created_ticket.getbuffer())
result = filecmp.cmp('created.png', 'reference_ticket.png', shallow=False)
print(result)
